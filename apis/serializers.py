from django.db.models import Sum
from rest_framework import serializers
from rewards.models import User, PaymentOption, RewardHistory, Product, ProductQRCode, RedemptionRequest
from rewards.models import PaymentOption, User

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'city', 'profession')

class PaymentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentOption
        fields = '__all__'
        read_only_fields = ('user',)


# User Profile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'city', 'profession')

# Payment Option Serializer
class PaymentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentOption
        fields = ('id', 'type', 'upi_id', 'bank_account', 'ifsc_code', 'holder_name', 'created_at')
        read_only_fields = ('user', 'created_at')

    def validate(self, data):
        # If type is UPI, then upi_id must be provided
        if data.get('type') == 'upi' and not data.get('upi_id'):
            raise serializers.ValidationError("UPI ID is required for UPI payment method.")
        # If type is bank, then bank_account, ifsc_code, and holder_name must be provided
        if data.get('type') == 'bank':
            if not data.get('bank_account'):
                raise serializers.ValidationError("Bank account is required for bank payment method.")
            if not data.get('ifsc_code'):
                raise serializers.ValidationError("IFSC code is required for bank payment method.")
            if not data.get('holder_name'):
                raise serializers.ValidationError("Holder name is required for bank payment method.")
        return data

# Reward History Serializer
class RewardHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = RewardHistory
        fields = ('id', 'product', 'product_name', 'qr_code', 'points_earned', 'created_at')
        read_only_fields = ('user', 'points_earned', 'created_at')

# Product QR Code Serializer (for scanning, we might only need to return minimal info)
class ProductQRCodeSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_points = serializers.IntegerField(source='product.points', read_only=True)

    class Meta:
        model = ProductQRCode
        fields = ('id', 'code', 'status', 'product_name', 'product_points', 'redeemed_at')
        read_only_fields = ('code', 'status', 'product', 'redeemed_by', 'redeemed_at')

# Redemption Request Serializer
class RedemptionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedemptionRequest
        fields = ('id', 'points', 'payment_method', 'status', 'created_at', 'updated_at')
        read_only_fields = ('user', 'status', 'created_at', 'updated_at')

    def validate_points(self, value):
        # Check if the user has enough points
        user = self.context['request'].user
        total_points = RewardHistory.objects.filter(user=user).aggregate(total=Sum('points_earned'))['total'] or 0
        if value > total_points:
            raise serializers.ValidationError("Insufficient points")
        return value