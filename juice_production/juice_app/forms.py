from django import forms
from .models import ProductionBatch, MaterialUsage, Product, PurchaseOrder, PurchaseOrderItem, Sale, SaleItem, UserProfile, RawMaterial, Customer, Bottle,Recipe
from django.contrib.auth.forms import UserCreationForm
from .validators import validate_phone_number
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User



class ProductionBatchForm(forms.ModelForm):
    """Form for creating and editing production batches."""
    class Meta:
        model = ProductionBatch
        fields = ['product', 'planned_quantity', 'actual_quantity_produced', 
                  'production_date', 'quality_check_passed', 'notes']
        widgets = {
            'production_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get the batch status from kwargs, if provided
        batch_status = kwargs.pop('batch_status', None)
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # For new batches, don't show actual_quantity_produced
        if not self.instance.pk:
            self.fields.pop('actual_quantity_produced')
            self.fields.pop('quality_check_passed')
        
        # For existing batches, make fields read-only unless the batch is in 'planned' status
        elif self.instance.pk:
            # Only make fields read-only if not in 'planned' status
            if batch_status != 'planned':
                self.fields['product'].disabled = True
                self.fields['planned_quantity'].disabled = True
class MaterialUsageForm(forms.ModelForm):
    """Form for recording material usage in production."""
    class Meta:
        model = MaterialUsage
        fields = ['actual_quantity_used', 'waste_quantity', 'notes']
        widgets = {
            'actual_quantity_used': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'waste_quantity': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actual_quantity_used'].required = True
        
        # Pre-populate with planned quantity if this is a new form
        if self.instance and not self.instance.actual_quantity_used and hasattr(self.instance, 'planned_quantity'):
            self.fields['actual_quantity_used'].initial = self.instance.planned_quantity


class UserLoginForm(forms.Form):
    """Form for user login."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class UserRegistrationForm(UserCreationForm):
    """Form for user registration."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    phone = forms.CharField(
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists")
        return email

class UserUpdateForm(forms.ModelForm):
    """Form for updating user information."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information."""
    phone = forms.CharField(
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'department']
        widgets = {
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }



class RawMaterialForm(forms.ModelForm):
    """Form for creating and editing raw materials."""
    class Meta:
        model = RawMaterial
        fields = ['name', 'unit', 'quantity_in_stock', 'unit_cost', 'supplier', 
                 'reorder_level', 'is_fruit', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Customer.objects.filter(is_supplier=True)


class BottleForm(forms.ModelForm):
    """Form for creating and editing bottle sizes."""
    class Meta:
        model = Bottle
        fields = ['size', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    """Form for creating and editing products."""
    class Meta:
        model = Product
        fields = ['name', 'bottle', 'description', 'ingredients_description',
                 'markup_percentage', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'ingredients_description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bottle'].queryset = Bottle.objects.filter(is_active=True).order_by('size')

class RecipeForm(forms.ModelForm):
    """Form for product recipe ingredients."""
    class Meta:
        model = Recipe
        fields = ['raw_material', 'quantity_required', 'is_primary', 'order', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raw_material'].queryset = RawMaterial.objects.all().order_by('name')


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers."""
    class Meta:
        model = Customer
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 
                 'is_supplier', 'is_buyer', 'credit_limit', 'payment_terms', 
                 'notes', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
class SaleForm(forms.ModelForm):
    """Form for creating and editing sales."""
    class Meta:
        model = Sale
        fields = ['customer', 'sale_date', 'notes']
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(is_buyer=True, is_active=True)

class SaleItemForm(forms.ModelForm):
    """Form for sale items."""
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True, stock_quantity__gt=0)
        
        # Pre-populate unit price if product is selected
        if self.instance and self.instance.product_id:
            self.fields['unit_price'].initial = self.instance.product.selling_price

class PurchaseOrderForm(forms.ModelForm):
    """Form for creating and editing purchase orders."""
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'order_date', 'expected_delivery_date', 'notes']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Customer.objects.filter(is_supplier=True, is_active=True)

class PurchaseOrderItemForm(forms.ModelForm):
    """Form for purchase order items."""
    class Meta:
        model = PurchaseOrderItem
        fields = ['raw_material', 'quantity_ordered', 'unit_price']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raw_material'].queryset = RawMaterial.objects.all().order_by('name')

class ReceiveItemForm(forms.Form):
    """Form for receiving items on a purchase order."""
    quantity_receiving = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        label="Quantity to Receive"
    )