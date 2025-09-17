from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import random
from apis.serializers import PaymentOptionSerializer, RewardHistorySerializer, UserProfileSerializer
from rewards.models import PaymentOption, ProductQRCode, RedemptionRequest, RewardHistory, User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging


logger = logging.getLogger('apis')


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
    try:
        otp = str(random.randint(1000, 9999))  # store as string for consistency
        cache_key = f"otp_{phone}"

        # store OTP in cache with expiry (e.g. 5 minutes = 300 sec)
        cache.set(cache_key, otp, timeout=300)
        logger.info("OTP generated and cached", extra={'phone_suffix': str(phone)[-4:] if phone else None})

        # for testing, return OTP in response
        return Response({'message': 'OTP sent successfully', 'otp': otp}, status=status.HTTP_200_OK)
    except Exception:
        logger.exception("Failed to send OTP", extra={'phone': phone})
        return Response({'error': 'Failed to send OTP'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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
    try:
        if otp_is_valid(phone, otp):
            user, created = User.objects.get_or_create(phone=phone)
            if created:
                user.is_phone_verified = True
                user.save()
                refresh = RefreshToken.for_user(user)
                logger.info("New user created via OTP", extra={'user_id': user.id})
                return Response({
                    'new_user': True,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })

            refresh = RefreshToken.for_user(user)
            logger.info("OTP verified for existing user", extra={'user_id': user.id})
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'profile_complete': bool(user.city and user.profession)
            })
        logger.warning("Invalid OTP attempt", extra={'phone': phone})
        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
    except TokenError:
        logger.exception("Token generation error", extra={'phone': phone})
        return Response({'error': 'Token generation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Unexpected error in verify_otp", extra={'phone': phone})
        return Response({'error': 'Verification failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@swagger_auto_schema(
    method="put",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="User's first name"),
            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="User's last name"),
            'city': openapi.Schema(type=openapi.TYPE_STRING, description="City name"),
            'profession': openapi.Schema(type=openapi.TYPE_STRING, description="User profession"),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description="Email address"),
        },
        required=['first_name', 'last_name'],  # adjust based on serializer
    ),
    responses={
        200: "Profile updated successfully",
        400: "Validation error",
    }
)
@api_view(['GET', 'PUT'])
def user_profile(request):
    try:
        if request.method == 'GET':
            serializer = UserProfileSerializer(request.user)
            return Response(serializer.data)

        elif request.method == 'PUT':
            serializer = UserProfileSerializer(request.user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info("User profile updated", extra={'user_id': getattr(request.user, 'id', None)})
                return Response(serializer.data)
            logger.warning("User profile validation failed", extra={'errors': serializer.errors})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("Error in user_profile", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Failed to process request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method="post",
    request_body=PaymentOptionSerializer,
    responses={201: PaymentOptionSerializer, 400: "Bad Request"},
)
@api_view(['GET', 'POST'])
def payment_methods(request):
    try:
        if request.method == 'GET':
            payments = PaymentOption.objects.filter(user=request.user)
            serializer = PaymentOptionSerializer(payments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = PaymentOptionSerializer(data=request.data)
            if serializer.is_valid():
                obj = serializer.save(user=request.user)
                logger.info("Payment method created", extra={'user_id': getattr(request.user, 'id', None), 'payment_id': getattr(obj, 'id', None)})
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.warning("Payment method create validation failed", extra={'errors': serializer.errors})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("Error in payment_methods", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Failed to process request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        product_qr = ProductQRCode.objects.get_by_plain_code(qr_code, status='unused')
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
        logger.info("QR code redeemed", extra={'user_id': getattr(request.user, 'id', None), 'qr_code': str(qr_code)})

        return Response({
            'success': True,
            'points_earned': product_qr.product.points,
            'product_name': product_qr.product.name
        })
    except ProductQRCode.DoesNotExist:
        logger.warning("Invalid or used QR code", extra={'qr_code': str(qr_code)})
        return Response({'error': 'Invalid or already used QR code'},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("Unexpected error in scan_qr_code", extra={'qr_code': str(qr_code)})
        return Response({'error': 'Failed to process QR code'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def reward_summary(request):
    try:
        total_points = RewardHistory.objects.filter(
            user=request.user
        ).aggregate(total=Sum('points_earned'))['total'] or 0

        redeemed_points = RedemptionRequest.objects.filter(
            user=request.user,
            status='pending'
        ).aggregate(total=Sum('points'))['total'] or 0

        return Response({
            'total_points': total_points,
            'redeemed_points': redeemed_points
        })
    except Exception:
        logger.exception("Error in reward_summary", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Failed to load summary'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def reward_history(request):
    try:
        history = RewardHistory.objects.filter(
            user=request.user
        ).order_by('-created_at')

        serializer = RewardHistorySerializer(history, many=True)
        return Response(serializer.data)
    except Exception:
        logger.exception("Error in reward_history", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Failed to load history'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "points": openapi.Schema(
                type=openapi.TYPE_INTEGER, description="Points to redeem"
            ),
            "payment_method_id": openapi.Schema(
                type=openapi.TYPE_INTEGER, description="Payment Method ID"
            ),
            "photo": openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_BINARY,   # <-- file input in Swagger
                description="Product photo",
            ),
        },
        required=["points", "payment_method_id", "photo"],
    ),
    responses={
        200: "Redemption created successfully",
        400: "Invalid request / insufficient points",
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def redeem_points(request):
    """Redeem reward points by selecting a payment method and uploading a proof photo."""
    # Guard: must be authenticated (endpoint currently AllowAny)
    if not getattr(request.user, 'is_authenticated', False):
        logger.warning("Unauthenticated redeem_points attempt")
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        points_str = request.data.get("points", 0)
        try:
            points_to_redeem = int(points_str)
        except (TypeError, ValueError):
            logger.warning("Invalid points value", extra={'points': points_str})
            return Response({"error": "Invalid points"}, status=status.HTTP_400_BAD_REQUEST)

        payment_method_id = request.data.get("payment_method_id")
        photo = request.FILES.get("photo")  # <-- uploaded file

        if not payment_method_id or photo is None:
            logger.warning("Missing fields for redemption", extra={'payment_method_id': payment_method_id, 'has_photo': photo is not None})
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        # total earned points
        total_points = (
            RewardHistory.objects.filter(user=request.user).aggregate(
                total=Sum("points_earned")
            )["total"]
            or 0
        )

        # check if user has enough points
        if points_to_redeem > total_points:
            logger.info("Insufficient points for redemption", extra={'user_id': getattr(request.user, 'id', None), 'requested': points_to_redeem, 'available': total_points})
            return Response(
                {"error": "Insufficient points"}, status=status.HTTP_400_BAD_REQUEST
            )

        # check if payment method exists
        try:
            payment_method = PaymentOption.objects.get(id=payment_method_id)
        except PaymentOption.DoesNotExist:
            logger.warning("Invalid payment method for redemption", extra={'payment_method_id': payment_method_id})
            return Response(
                {"error": "Invalid payment method"}, status=status.HTTP_400_BAD_REQUEST
            )

        # create redemption request
        redemption = RedemptionRequest.objects.create(
            user=request.user,
            points=points_to_redeem,
            payment_method=payment_method,
            status="pending",
            photo=photo,
        )
        logger.info("Redemption request created", extra={'user_id': getattr(request.user, 'id', None), 'redemption_id': redemption.id})

        return Response(
            {
                "success": True,
                "redemption_id": redemption.id,
                "status": redemption.status,
                "photo_url": redemption.photo.url if redemption.photo else None,
            },
            status=status.HTTP_200_OK,
        )
    except Exception:
        logger.exception("Unexpected error in redeem_points", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Redemption failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
def dashboard(request):
    try:
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
    except Exception:
        logger.exception("Error in dashboard", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Failed to load dashboard'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    try:
        password = request.data.get('password')
        uid = getattr(request.user, 'id', None)
        request.user.delete()
        logger.info("Account deleted", extra={'user_id': uid})
        return Response({'message': 'Account deleted successfully'})
    except Exception:
        logger.exception("Error deleting account", extra={'user_id': getattr(request.user, 'id', None)})
        return Response({'error': 'Failed to delete account'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
