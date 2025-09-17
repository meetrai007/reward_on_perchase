import base64
from io import BytesIO
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import qrcode
from django.core.files.base import ContentFile
from django.db import models
from django.conf import settings
import uuid


# Custom User Manager for phone-based login
class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("The phone number must be set")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)  # not really used if OTP login, but required internally
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra_fields)


# Custom User Model (Phone only, no username/email)
class User(AbstractUser):
    username = None   # remove username field
    email = None      # remove email field

    phone = models.CharField(max_length=20, unique=True)
    city = models.CharField(max_length=100, blank=True)
    profession = models.CharField(max_length=200, blank=True)
    is_phone_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "phone"   # login with phone
    REQUIRED_FIELDS = []       # no username/email required

    objects = UserManager()

    def __str__(self):
        return f"{self.phone}"


# Payment Options (Bank / UPI)
class PaymentOption(models.Model):
    PAYMENT_CHOICES = (
        ("upi", "UPI"),
        ("bank", "Bank"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    type = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    upi_id = models.CharField(max_length=255, blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    holder_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone} - {self.type}"


from django.db import models


# Product Category (optional but useful for grouping)
class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# Product Model
class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="media/products/", blank=True, null=True)
    points = models.PositiveIntegerField(default=0)  # reward points for this product
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# QR Code Model
class ProductQRCode(models.Model):
    STATUS_CHOICES = (
        ("unused", "Unused"),
        ("redeemed", "Redeemed"),
    )

    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="qrcodes")
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)  # unique QR identifier
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="unused")
    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redeemed_qrcodes"
    )
    redeemed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_qr_code(self):
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data - using the code as redemption data
        redemption_url = f"http://192.168.1.9:8000/redeem/{self.code}/"
        qr.add_data(redemption_url)
        qr.make(fit=True)
        
        # Create an image from the QR Code instance
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for HTML embedding
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"

    def __str__(self):
        return f"{self.product.name} - {self.code} - {self.status}"

# Reward History
class RewardHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reward_history")
    product = models.ForeignKey("Product", on_delete=models.SET_NULL, null=True)
    qr_code = models.OneToOneField("ProductQRCode", on_delete=models.CASCADE, related_name="reward_history")
    points_earned = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone} earned {self.points_earned} points"


class RedemptionRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="redemption_requests")
    points = models.PositiveIntegerField()
    payment_method = models.ForeignKey(PaymentOption, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    photo = models.ImageField(upload_to="redemptions/", blank=True, null=True)  # <-- added field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.phone} - {self.points} points - {self.status}"
