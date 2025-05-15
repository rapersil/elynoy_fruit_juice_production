from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.forms import inlineformset_factory
from django.db.models import Q
from ..models import Product, Bottle, Recipe, RawMaterial
from django import forms
from ..forms import RecipeForm, ProductForm


@login_required
@login_required
def product_list(request):
    """Display list of products with filtering and search functionality."""
    # Get all bottle sizes for filter dropdown
    all_bottles = Bottle.objects.filter(is_active=True).order_by('size')
    
    # Initialize filter variables
    filter_status = request.GET.get('status', 'all')
    filter_bottle = request.GET.get('bottle', 'all')
    filter_stock = request.GET.get('stock', 'all')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with all products
    products = Product.objects.all()
    
    # Apply status filter
    if filter_status == 'active':
        products = products.filter(is_active=True)
    elif filter_status == 'inactive':
        products = products.filter(is_active=False)
    
    # Apply bottle filter
    if filter_bottle != 'all':
        products = products.filter(bottle_id=filter_bottle)
    
    # Apply stock filter
    if filter_stock == 'in_stock':
        products = products.filter(stock_quantity__gt=0)
    elif filter_stock == 'out_of_stock':
        products = products.filter(stock_quantity=0)
    elif filter_stock == 'low_stock':
        products = products.filter(stock_quantity__gt=0, stock_quantity__lte=10)  # Assuming 10 is low stock threshold
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'price_low':
        products = products.order_by('selling_price')
    elif sort_by == 'price_high':
        products = products.order_by('-selling_price')
    elif sort_by == 'stock_low':
        products = products.order_by('stock_quantity')
    elif sort_by == 'stock_high':
        products = products.order_by('-stock_quantity')
    
    # Calculate summary statistics
    total_products = products.count()
    active_products = products.filter(is_active=True).count()
    out_of_stock = products.filter(stock_quantity=0).count()
    low_stock = products.filter(stock_quantity__gt=0, stock_quantity__lte=10).count()
    
    # Calculate inventory value
    total_inventory_value = sum(
        product.stock_quantity * product.selling_price 
        for product in products
    )
    
    context = {
        'products': products,
        'all_bottles': all_bottles,
        'filter_status': filter_status,
        'filter_bottle': filter_bottle,
        'filter_stock': filter_stock,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_products': total_products,
        'active_products': active_products,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'total_inventory_value': total_inventory_value,
    }
    
    return render(request, 'juice_app/product/product_list.html', context)

@login_required
def product_detail(request, product_id):
    """Display details of a product."""
    product = get_object_or_404(Product, id=product_id)
    recipe = product.ingredients.all().order_by('order')
    return render(request, 'juice_app/product/product_detail.html', 
                 {'product': product, 'recipe': recipe})

@login_required
def product_new(request):
    """Create a new product with recipe and automatic SKU generation."""
    RecipeFormSet = inlineformset_factory(
        Product, Recipe, form=RecipeForm, extra=3, can_delete=True
    )
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create product without saving yet
                product = form.save(commit=False)
                
                # Generate SKU based on bottle size
                bottle = form.cleaned_data.get('bottle')
                if bottle:
                    product.sku = Product.generate_sku(bottle.size)
                else:
                    product.sku = Product.generate_sku(None)
                
                # Set production_cost to 0 initially, it will be calculated by signals
                product.production_cost = 0
                
                if hasattr(product, 'created_by'):
                    product.created_by = request.user
                
                product.save()
                
                # Process recipe formset
                formset = RecipeFormSet(request.POST, instance=product)
                if formset.is_valid():
                    formset.save()
                    messages.success(request, f'Product "{product.name}" created successfully with SKU: {product.sku}')
                    return redirect('product_detail', product_id=product.id)
        else:
            formset = RecipeFormSet(request.POST)
    else:
        form = ProductForm()
        formset = RecipeFormSet()
    
    return render(request, 'juice_app/product/product_form.html', 
                 {'form': form, 'formset': formset, 'title': 'New Product'})

@login_required
def product_edit(request, product_id):
    """Edit an existing product and its recipe with permission checks."""
    product = get_object_or_404(Product, id=product_id)
    
    # Permission check: only admin/superadmin or creator can edit
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = hasattr(product, 'created_by') and product.created_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to edit this product.')
        return redirect('product_detail', product_id=product.id)
    
    RecipeFormSet = inlineformset_factory(
        Product, Recipe, form=RecipeForm, extra=1, can_delete=True
    )
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        formset = RecipeFormSet(request.POST, instance=product)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # SKU remains unchanged for existing products
                form.save()
                formset.save()
                messages.success(request, f'Product "{product.name}" updated successfully.')
                return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
        formset = RecipeFormSet(instance=product)
    
    # Add SKU as a read-only field in the context
    context = {
        'form': form, 
        'formset': formset, 
        'title': 'Edit Product', 
        'product': product,
        'sku_display': product.sku  # Pass SKU for display in template
    }
    
    return render(request, 'juice_app/product/product_form.html', context)