from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
import csv
from .models import Product, ProductQRCode, User, RewardHistory, ProductCategory, PaymentOption
from .forms import ProductForm, QRCodeGenerateForm

from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AdminAuthenticationForm

# Check if user is admin/staff
def is_staff_user(user):
    return user.is_staff

def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard_home')
    
    if request.method == 'POST':
        form = AdminAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('dashboard_home')
    else:
        form = AdminAuthenticationForm()
    
    return render(request, 'admin/login.html', {'form': form})

@login_required
@user_passes_test(is_staff_user)
def admin_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')

# Dashboard home
@login_required
@user_passes_test(is_staff_user)
def dashboard_home(request):
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_qr_codes = ProductQRCode.objects.count()
    redeemed_qr_codes = ProductQRCode.objects.filter(status='redeemed').count()
    
    context = {
        'total_products': total_products,
        'total_users': total_users,
        'total_qr_codes': total_qr_codes,
        'redeemed_qr_codes': redeemed_qr_codes,
    }
    return render(request, 'dashboard/home.html', context)

# Product views
@login_required
@user_passes_test(is_staff_user)
def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard/products/list.html', {'page_obj': page_obj})

@login_required
@user_passes_test(is_staff_user)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'dashboard/products/form.html', {'form': form, 'title': 'Add Product'})

@login_required
@user_passes_test(is_staff_user)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'dashboard/products/form.html', {'form': form, 'title': 'Edit Product'})

@login_required
@user_passes_test(is_staff_user)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('product_list')
    
    return render(request, 'dashboard/products/delete.html', {'product': product})

# QR Code views
@login_required
@user_passes_test(is_staff_user)
def qrcode_list(request):
    qrcodes = ProductQRCode.objects.all().order_by('-created_at')
    product_filter = request.GET.get('product')
    status_filter = request.GET.get('status')
    
    if product_filter:
        qrcodes = qrcodes.filter(product_id=product_filter)
    if status_filter:
        qrcodes = qrcodes.filter(status=status_filter)
    
    paginator = Paginator(qrcodes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    products = Product.objects.all()
    
    return render(request, 'dashboard/qrcodes/list.html', {
        'page_obj': page_obj,
        'products': products,
        'product_filter': product_filter,
        'status_filter': status_filter
    })

@login_required
@user_passes_test(is_staff_user)
def qrcode_generate(request):
    if request.method == 'POST':
        form = QRCodeGenerateForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            
            # Generate QR codes
            qrcodes = []
            for _ in range(quantity):
                qr = ProductQRCode.objects.create(product=product)
                qrcodes.append(qr)
            
            # Prepare data for printing
            request.session['qrcodes_to_print'] = [str(qr.code) for qr in qrcodes]
            messages.success(request, f'{quantity} QR codes generated successfully!')
            return redirect('qrcode_print')
    else:
        form = QRCodeGenerateForm()
    
    return render(request, 'dashboard/qrcodes/generate.html', {'form': form})

@login_required
@user_passes_test(is_staff_user)
def qrcode_print(request):
    qrcode_ids = request.session.get('qrcodes_to_print', [])
    qrcodes = ProductQRCode.objects.filter(code__in=qrcode_ids)
    
    # Clear the session after retrieving
    if 'qrcodes_to_print' in request.session:
        del request.session['qrcodes_to_print']
    
    return render(request, 'dashboard/qrcodes/print.html', {'qrcodes': qrcodes})

@login_required
@user_passes_test(is_staff_user)
def qrcode_print_filtered(request):
    # Get filter parameters from the request
    product_filter = request.GET.get('product', '')
    status_filter = request.GET.get('status', '')
    
    # Apply the same filtering logic as in your list view
    qrcodes = ProductQRCode.objects.all()
    
    if product_filter:
        qrcodes = qrcodes.filter(product_id=product_filter)
    
    if status_filter:
        qrcodes = qrcodes.filter(status=status_filter)
    
    return render(request, 'dashboard/qrcodes/print_filtered.html', {
        'qrcodes': qrcodes,
        'product_filter': product_filter,
        'status_filter': status_filter
    })

# User views
@login_required
@user_passes_test(is_staff_user)
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard/users/list.html', {'page_obj': page_obj})

@login_required
@user_passes_test(is_staff_user)
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    reward_history = RewardHistory.objects.filter(user=user).order_by('-created_at')
    payment_options = PaymentOption.objects.filter(user=user)
    
    context = {
        'user_obj': user,  # Using 'user_obj' to avoid conflict with request.user
        'reward_history': reward_history,
        'payment_options': payment_options,
    }
    return render(request, 'dashboard/users/detail.html', context)

# Reward History views
@login_required
@user_passes_test(is_staff_user)
def reward_history(request):
    rewards = RewardHistory.objects.all().order_by('-created_at')
    user_filter = request.GET.get('user')
    product_filter = request.GET.get('product')
    
    if user_filter:
        rewards = rewards.filter(user_id=user_filter)
    if product_filter:
        rewards = rewards.filter(product_id=product_filter)
    
    paginator = Paginator(rewards, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    users = User.objects.all()
    products = Product.objects.all()
    
    return render(request, 'dashboard/rewards/history.html', {
        'page_obj': page_obj,
        'users': users,
        'products': products,
        'user_filter': user_filter,
        'product_filter': product_filter
    })

# Export data views
@login_required
@user_passes_test(is_staff_user)
def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Phone', 'City', 'Profession', 'Date Joined', 'Last Login'])
    
    users = User.objects.all().values_list('phone', 'city', 'profession', 'date_joined', 'last_login')
    for user in users:
        writer.writerow(user)
    
    return response

@login_required
@user_passes_test(is_staff_user)
def export_rewards_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rewards.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['User Phone', 'Product', 'Points Earned', 'Date'])
    
    rewards = RewardHistory.objects.select_related('user', 'product').all()
    for reward in rewards:
        writer.writerow([
            reward.user.phone,
            reward.product.name if reward.product else 'N/A',
            reward.points_earned,
            reward.created_at
        ])
    
    return response

# Static pages for mobile app
def about_page(request):
    return render(request, 'mobile_pages/about.html')

def contact_page(request):
    return render(request, 'mobile_pages/contact.html')

def privacy_policy_page(request):
    return render(request, 'mobile_pages/privacy_policy.html')

def delete_account_page(request):
    return render(request, 'mobile_pages/delete_account.html')