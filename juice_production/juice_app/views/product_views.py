from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.forms import inlineformset_factory
from ..models import Product, Bottle, Recipe, RawMaterial
from django import forms
from ..forms import RecipeForm, ProductForm


@login_required
def product_list(request):
    """Display list of products."""
    products = Product.objects.all().order_by('name')
    return render(request, 'juice_app/product/product_list.html', {'products': products})

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