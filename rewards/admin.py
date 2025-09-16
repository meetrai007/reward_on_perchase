from django.contrib import admin
from .models import ProductCategory, Product, ProductQRCode, User, RewardHistory, PaymentOption

# Register your models here.
admin.site.register(ProductCategory)
admin.site.register(Product)
admin.site.register(ProductQRCode)
admin.site.register(User)
admin.site.register(RewardHistory)
admin.site.register(PaymentOption)