from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
import csv
import logging
from .models import Product, ProductQRCode, User, RewardHistory, PaymentOption
from .forms import ProductForm, QRCodeGenerateForm
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseNotFound
from .models import ProductQRCode
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AdminAuthenticationForm

# Module logger
logger = logging.getLogger('rewards')

# Check if user is admin/staff
def is_staff_user(user):
    return user.is_staff

def admin_login(request):
    try:
        if request.user.is_authenticated and request.user.is_staff:
            logger.info("Admin already authenticated, redirecting to dashboard", extra={'user_id': request.user.id, 'path': request.path})
            return redirect('dashboard_home')
        
        if request.method == 'POST':
            form = AdminAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                auth_login(request, user)
                logger.info("Admin login successful", extra={'user_id': user.id})
                return redirect('dashboard_home')
            else:
                logger.warning("Admin login failed", extra={'errors': str(form.errors)})
        else:
            form = AdminAuthenticationForm()
        
        return render(request, 'admin/login.html', {'form': form})
        
    except Exception:
        logger.exception("Unexpected error in admin_login", extra={'path': request.path})
        messages.error(request, 'Unexpected error. Please try again.')
        return render(request, 'admin/login.html', {'form': AdminAuthenticationForm()})

@login_required
@user_passes_test(is_staff_user)
def admin_logout(request):
    try:
        logger.info("Admin logging out", extra={'user_id': getattr(request.user, 'id', None)})
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('admin_login')
    except Exception:
        logger.exception("Error during admin_logout")
        messages.error(request, 'Logout failed. Please try again.')
        return redirect('dashboard_home')

# Dashboard home
@login_required
@user_passes_test(is_staff_user)
def dashboard_home(request):
    try:
        total_products = Product.objects.count()
        total_users = User.objects.count()
        total_qr_codes = ProductQRCode.objects.count()
        redeemed_qr_codes = ProductQRCode.objects.filter(status='redeemed').count()
        logger.debug("Dashboard metrics computed", extra={'total_products': total_products, 'total_users': total_users, 'total_qr_codes': total_qr_codes, 'redeemed_qr_codes': redeemed_qr_codes})
        context = {
            'total_products': total_products,
            'total_users': total_users,
            'total_qr_codes': total_qr_codes,
            'redeemed_qr_codes': redeemed_qr_codes,
        }
        return render(request, 'dashboard/home.html', context)
    except Exception:
        logger.exception("Failed to load dashboard metrics")
        messages.error(request, 'Failed to load dashboard.')
        return render(request, 'dashboard/home.html', {'total_products': 0, 'total_users': 0, 'total_qr_codes': 0, 'redeemed_qr_codes': 0})

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
    try:
        if request.method == 'POST':
            form = ProductForm(request.POST, request.FILES)
            if form.is_valid():
                product = form.save()
                logger.info("Product created", extra={'product_id': getattr(product, 'id', None)})
                messages.success(request, 'Product created successfully!')
                return redirect('product_list')
            else:
                logger.warning("Product create form invalid", extra={'errors': str(form.errors)})
        else:
            form = ProductForm()
        
        return render(request, 'dashboard/products/form.html', {'form': form, 'title': 'Add Product'})
    except Exception:
        logger.exception("Unexpected error in product_create")
        messages.error(request, 'Could not create product. Please try again.')
        return redirect('product_list')

@login_required
@user_passes_test(is_staff_user)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        if request.method == 'POST':
            form = ProductForm(request.POST, request.FILES, instance=product)
            if form.is_valid():
                product = form.save()
                logger.info("Product updated", extra={'product_id': getattr(product, 'id', None)})
                messages.success(request, 'Product updated successfully!')
                return redirect('product_list')
            else:
                logger.warning("Product edit form invalid", extra={'errors': str(form.errors)})
        else:
            form = ProductForm(instance=product)
        
        return render(request, 'dashboard/products/form.html', {'form': form, 'title': 'Edit Product'})
    except Exception:
        logger.exception("Unexpected error in product_edit", extra={'product_id': pk})
        messages.error(request, 'Could not update product. Please try again.')
        return redirect('product_list')

@login_required
@user_passes_test(is_staff_user)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        if request.method == 'POST':
            logger.info("Deleting product", extra={'product_id': getattr(product, 'id', None)})
            product.delete()
            messages.success(request, 'Product deleted successfully!')
            return redirect('product_list')
        
        return render(request, 'dashboard/products/delete.html', {'product': product})
    except Exception:
        logger.exception("Unexpected error in product_delete", extra={'product_id': pk})
        messages.error(request, 'Could not delete product. Please try again.')
        return redirect('product_list')

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
    
    logger.debug("QR code list filtered", extra={'product_filter': product_filter, 'status_filter': status_filter, 'count': qrcodes.count()})
    return render(request, 'dashboard/qrcodes/list.html', {
        'page_obj': page_obj,
        'products': products,
        'product_filter': product_filter,
        'status_filter': status_filter
    })

@login_required
@user_passes_test(is_staff_user)
def qrcode_generate(request):
    try:
        if request.method == 'POST':
            form = QRCodeGenerateForm(request.POST)
            if form.is_valid():
                product = form.cleaned_data['product']
                quantity = form.cleaned_data['quantity']
                logger.info("Generating QR codes", extra={'product_id': getattr(product, 'id', None), 'quantity': quantity})
                
                qrcodes = []
                for _ in range(quantity):
                    qr = ProductQRCode.objects.create(product=product)
                    qrcodes.append(qr)
                
                request.session['qrcodes_to_print'] = [str(qr.code) for qr in qrcodes]
                messages.success(request, f'{quantity} QR codes generated successfully!')
                return redirect('qrcode_print')
            else:
                logger.warning("QRCode generate form invalid", extra={'errors': str(form.errors)})
        else:
            form = QRCodeGenerateForm()
        
        return render(request, 'dashboard/qrcodes/generate.html', {'form': form})
    except Exception:
        logger.exception("Unexpected error in qrcode_generate")
        messages.error(request, 'Failed to generate QR codes. Please try again.')
        return redirect('qrcode_list')

@login_required
@user_passes_test(is_staff_user)
def qrcode_print(request):
    qrcode_ids = request.session.get('qrcodes_to_print', [])
    qrcodes = ProductQRCode.objects.filter(code__in=qrcode_ids)
    logger.debug("Preparing QR codes for print", extra={'count': qrcodes.count()})
    
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
    logger.debug("User list accessed", extra={'count': users.count()})
    
    return render(request, 'dashboard/users/list.html', {'page_obj': page_obj})

@login_required
@user_passes_test(is_staff_user)
def user_detail(request, pk):
    try:
        user = get_object_or_404(User, pk=pk)
        reward_history = RewardHistory.objects.filter(user=user).order_by('-created_at')
        payment_options = PaymentOption.objects.filter(user=user)
        logger.debug("User detail viewed", extra={'user_id': user.id, 'history_count': reward_history.count()})
        
        context = {
            'user_obj': user,  # Using 'user_obj' to avoid conflict with request.user
            'reward_history': reward_history,
            'payment_options': payment_options,
        }
        return render(request, 'dashboard/users/detail.html', context)
    except Exception:
        logger.exception("Error loading user_detail", extra={'user_id': pk})
        messages.error(request, 'Failed to load user details.')
        return redirect('user_list')

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
    logger.debug("Reward history filtered", extra={'user_filter': user_filter, 'product_filter': product_filter, 'count': rewards.count()})
    
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
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Phone', 'City', 'Profession', 'Date Joined', 'Last Login'])
        
        rows = list(User.objects.all().values_list('phone', 'city', 'profession', 'date_joined', 'last_login'))
        for row in rows:
            writer.writerow(row)
        logger.info("Users CSV exported", extra={'count': len(rows)})
        return response
    except Exception:
        logger.exception("Failed to export users CSV")
        return HttpResponse("Failed to export users", status=500)

@login_required
@user_passes_test(is_staff_user)
def export_rewards_csv(request):
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rewards.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User Phone', 'Product', 'Points Earned', 'Date'])
        
        rewards = RewardHistory.objects.select_related('user', 'product').all()
        count = 0
        for reward in rewards:
            writer.writerow([
                reward.user.phone,
                reward.product.name if reward.product else 'N/A',
                reward.points_earned,
                reward.created_at
            ])
            count += 1
        logger.info("Rewards CSV exported", extra={'count': count})
        return response
    except Exception:
        logger.exception("Failed to export rewards CSV")
        return HttpResponse("Failed to export rewards", status=500)


def qr_code_status(request, uuid_str):
    try:
        qr_code = ProductQRCode.objects.filter(code=uuid_str).first()
        if not qr_code:
            logger.warning("QR code not found", extra={'code': uuid_str})
            return HttpResponseNotFound("QR code not found")
        context = {
            'status': qr_code.status,
        }
        logger.debug("QR code status fetched", extra={'code': uuid_str, 'status': qr_code.status})
        return render(request, 'public/qr_code_status.html', context)
    except Exception:
        logger.exception("Error resolving qr_code_status", extra={'code': uuid_str})
        return HttpResponseNotFound("Invalid QR code")

# Static pages for mobile app
def about_page(request):
    return render(request, 'mobile_pages/about.html')

def contact_page(request):
    return render(request, 'mobile_pages/contact.html')

def privacy_policy_page(request):
    return render(request, 'mobile_pages/privacy_policy.html')

def delete_account_page(request):
    return render(request, 'mobile_pages/delete_account.html')