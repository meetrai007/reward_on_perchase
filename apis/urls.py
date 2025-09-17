# urls.py
from django.urls import path
from apis import views

urlpatterns = [
    path('send-otp/', views.send_otp),
    path('verify-otp/', views.verify_otp),
    path('profile/', views.user_profile),
    path('payment-methods/', views.payment_methods),
    path('scan-qr/', views.scan_qr_code),
    path('reward-summary/', views.reward_summary),
    path('reward-history/', views.reward_history),
    path('redeem-points/', views.redeem_points),
    path('dashboard/', views.dashboard),
    path('delete-account/', views.delete_account),
]