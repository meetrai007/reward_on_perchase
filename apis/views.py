from functools import cache
from time import timezone
from django.db.models import Sum
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import random
from apis.serializers import PaymentOptionSerializer, RewardHistorySerializer, UserProfileSerializer
from rewards.models import PaymentOption, ProductQRCode, RedemptionRequest, RewardHistory, User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def otp_is_valid(phone, otp):
    """
    Validate OTP against stored value in cache
    """
    cache_key = f"otp_{phone}"
    stored_otp = cache.get(cache_key)

    if stored_otp and stored_otp == otp:
        cache.delete(cache_key)
        return True
    return False


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'phone': openapi.Schema(type=openapi.TYPE_STRING, description="User phone number"),
        },
        required=['phone'],
    ),
    responses={200: "OTP sent successfully", 400: "Bad Request"},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    phone = request.data.get('phone')
    otp = random.randint(1000, 9999)
    return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'phone': openapi.Schema(type=openapi.TYPE_STRING, description="User phone number"),
            'otp': openapi.Schema(type=openapi.TYPE_STRING, description="One-Time Password"),
        },
        required=['phone', 'otp'],
    ),
    responses={200: "Tokens or new user", 400: "Invalid OTP"},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    phone = request.data.get('phone')
    otp = request.data.get('otp')

    if otp_is_valid(phone, otp):
        user, created = User.objects.get_or_create(phone=phone)
        if created:
            user.is_phone_verified = True
            user.save()
            return Response({'new_user': True, 'token': user.get_auth_token()})

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'profile_complete': bool(user.city and user.profession)
        })
    return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
def user_profile(request):
    if request.method == 'GET':
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserProfileSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="post",
    request_body=PaymentOptionSerializer,
    responses={201: PaymentOptionSerializer, 400: "Bad Request"},
)
@api_view(['GET', 'POST'])
def payment_methods(request):
    if request.method == 'GET':
        payments = PaymentOption.objects.filter(user=request.user)
        serializer = PaymentOptionSerializer(payments, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PaymentOptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'qr_code': openapi.Schema(type=openapi.TYPE_STRING, description="Scanned QR Code"),
        },
        required=['qr_code'],
    ),
    responses={200: "Points earned", 400: "Invalid QR code"},
)
@api_view(['POST'])
def scan_qr_code(request):
    qr_code = request.data.get('qr_code')
    try:
        product_qr = ProductQRCode.objects.get(code=qr_code, status='unused')
        product_qr.status = 'redeemed'
        product_qr.redeemed_by = request.user
        product_qr.redeemed_at = timezone.now()
        product_qr.save()

        reward = RewardHistory.objects.create(
            user=request.user,
            product=product_qr.product,
            qr_code=product_qr,
            points_earned=product_qr.product.points
        )

        return Response({
            'success': True,
            'points_earned': product_qr.product.points,
            'product_name': product_qr.product.name
        })
    except ProductQRCode.DoesNotExist:
        return Response({'error': 'Invalid or already used QR code'},
                        status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def reward_summary(request):
    total_points = RewardHistory.objects.filter(
        user=request.user
    ).aggregate(total=Sum('points_earned'))['total'] or 0

    return Response({
        'total_points': total_points,
        'redeemable_points': total_points
    })


@api_view(['GET'])
def reward_history(request):
    history = RewardHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')

    serializer = RewardHistorySerializer(history, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'points': openapi.Schema(type=openapi.TYPE_INTEGER, description="Points to redeem"),
            'payment_method_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Payment Method ID"),
        },
        required=['points', 'payment_method_id'],
    ),
    responses={200: "Redemption created", 400: "Insufficient points"},
)
@api_view(['POST'])
def redeem_points(request):
    points_to_redeem = request.data.get('points')
    payment_method_id = request.data.get('payment_method_id')

    total_points = RewardHistory.objects.filter(
        user=request.user
    ).aggregate(total=Sum('points_earned'))['total'] or 0

    if points_to_redeem > total_points:
        return Response({'error': 'Insufficient points'},
                        status=status.HTTP_400_BAD_REQUEST)

    redemption = RedemptionRequest.objects.create(
        user=request.user,
        points=points_to_redeem,
        payment_method_id=payment_method_id,
        status='pending'
    )

    return Response({
        'success': True,
        'redemption_id': redemption.id,
        'status': 'pending'
    })


@api_view(['GET'])
def dashboard(request):
    total_points = RewardHistory.objects.filter(
        user=request.user
    ).aggregate(total=Sum('points_earned'))['total'] or 0

    recent_activity = RewardHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    serializer = RewardHistorySerializer(recent_activity, many=True)

    return Response({
        'total_points': total_points,
        'recent_activity': serializer.data
    })


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'password': openapi.Schema(type=openapi.TYPE_STRING, description="Account password (optional)"),
        },
    ),
    responses={200: "Account deleted"},
)
@api_view(['POST'])
def delete_account(request):
    password = request.data.get('password')
    request.user.delete()
    return Response({'message': 'Account deleted successfully'})
