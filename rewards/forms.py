from django import forms
from .models import Product, ProductQRCode
from django.contrib.auth.forms import AuthenticationForm

class AdminAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'image', 'points', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class QRCodeGenerateForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        empty_label="Select a product"
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=10,
        help_text="Number of QR codes to generate (max 100 at a time)"
    )