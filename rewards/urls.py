from django.urls import path
from . import views

urlpatterns = [
    # Admin Authentication URLs
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    # login
    path('accounts/login/', views.admin_login, name='admin_login'),

    # Dashboard
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # QR Codes
    path('qrcodes/', views.qrcode_list, name='qrcode_list'),
    path('qrcodes/generate/', views.qrcode_generate, name='qrcode_generate'),
    path('qrcodes/print/', views.qrcode_print, name='qrcode_print'),
    path('qrcodes/print-filtered/', views.qrcode_print_filtered, name='qrcode_print_filtered'),
    
    # Users
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    
    # Reward History
    path('rewards/', views.reward_history, name='reward_history'),
    
    # Export
    path('export/users/csv/', views.export_users_csv, name='export_users_csv'),
    path('export/rewards/csv/', views.export_rewards_csv, name='export_rewards_csv'),

    # mobile apps pages 
    path('mobile/about/', views.about_page, name='mobile_about'),
    path('mobile/contact/', views.contact_page, name='mobile_contact'),
    path('mobile/privacy-policy/', views.privacy_policy_page, name='mobile_privacy_policy'),
    path('mobile/delete-account/', views.delete_account_page, name='mobile_delete_account'),
]