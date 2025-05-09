from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F, Sum, DecimalField, ExpressionWrapper, Q
from ..models import RawMaterial, Customer
from django import forms
from ..forms import RawMaterialForm

@login_required
def raw_material_list(request):
    """Display list of raw materials with filtering and search functionality."""
    # Get all suppliers for filter dropdown
    all_suppliers = Customer.objects.filter(is_supplier=True, is_active=True).order_by('name')
    
    # Initialize filter variables
    filter_type = request.GET.get('type', 'all')
    filter_status = request.GET.get('status', 'all')
    filter_supplier = request.GET.get('supplier', 'all')
    search_query = request.GET.get('search', '')
    
    # Start with all materials
    materials = RawMaterial.objects.all()
    
    # Apply material type filter
    if filter_type == 'fruits':
        materials = materials.filter(is_fruit=True)
    elif filter_type == 'other':
        materials = materials.filter(is_fruit=False)
    
    # Apply stock status filter
    if filter_status == 'low_stock':
        materials = materials.filter(quantity_in_stock__lte=F('reorder_level'))
    elif filter_status == 'out_of_stock':
        materials = materials.filter(quantity_in_stock=0)
    elif filter_status == 'in_stock':
        materials = materials.filter(quantity_in_stock__gt=F('reorder_level'))
    
    # Apply supplier filter
    if filter_supplier != 'all':
        materials = materials.filter(supplier_id=filter_supplier)
    
    # Apply search filter
    if search_query:
        materials = materials.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Get materials with low stock for the low stock panel
    low_stock = materials.filter(quantity_in_stock__lte=F('reorder_level'))
    
    # Calculate count of fruit materials
    fruit_count = materials.filter(is_fruit=True).count()
    
    # Calculate total materials count
    total_materials = materials.count()
    
    # Calculate inventory values
    total_inventory_value = sum(
        material.quantity_in_stock * material.unit_cost 
        for material in materials
    )
    
    low_stock_value = sum(
        material.quantity_in_stock * material.unit_cost 
        for material in low_stock
    )
    
    # Order the materials by name
    materials = materials.order_by('name')
    
    context = {
        'materials': materials,
        'low_stock': low_stock,
        'all_suppliers': all_suppliers,
        'filter_type': filter_type,
        'filter_status': filter_status,
        'filter_supplier': filter_supplier,
        'search_query': search_query,
        'fruit_count': fruit_count,
        'total_materials': total_materials,
        'total_inventory_value': total_inventory_value,
        'low_stock_value': low_stock_value,
    }
    
    return render(request, 'juice_app/raw_material/raw_material_list.html', context)

@login_required
def raw_material_detail(request, material_id):
    """Display details of a raw material."""
    material = get_object_or_404(RawMaterial, id=material_id)
    
    # Get recipes that use this material
    recipes = material.recipe_set.all()
    
    # Get purchase history
    purchase_history = []  # This would need to be fetched from PurchaseOrderItem
    
    context = {
        'material': material,
        'recipes': recipes,
        'purchase_history': purchase_history,
        'can_edit': request.user.profile.role in ['admin', 'superadmin'] or 
                   (hasattr(material, 'created_by') and material.created_by == request.user)
    }
    
    return render(request, 'juice_app/raw_material/raw_material_detail.html', context)

@login_required
def raw_material_new(request):
    """Create a new raw material."""
    if request.method == 'POST':
        form = RawMaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            if hasattr(material, 'created_by'):
                material.created_by = request.user
            material.save()
            messages.success(request, f'Raw material "{material.name}" created successfully.')
            return redirect('raw_material_list')
    else:
        form = RawMaterialForm()
    
    return render(request, 'juice_app/raw_material/raw_material_form.html', 
                 {'form': form, 'title': 'New Raw Material'})

@login_required
def raw_material_edit(request, material_id):
    """Edit an existing raw material with permission checks."""
    material = get_object_or_404(RawMaterial, id=material_id)
    
    # Permission check: only admin/superadmin or creator can edit
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = hasattr(material, 'created_by') and material.created_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to edit this raw material.')
        return redirect('raw_material_detail', material_id=material.id)
    
    if request.method == 'POST':
        form = RawMaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, f'Raw material "{material.name}" updated successfully.')
            return redirect('raw_material_detail', material_id=material.id)
    else:
        form = RawMaterialForm(instance=material)
    
    return render(request, 'juice_app/raw_material/raw_material_form.html', 
                 {'form': form, 'title': 'Edit Raw Material', 'material': material})

@login_required
def raw_material_delete(request, material_id):
    """Delete a raw material with permission checks."""
    material = get_object_or_404(RawMaterial, id=material_id)
    
    # Permission check: only admin/superadmin or creator can delete
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = hasattr(material, 'created_by') and material.created_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to delete this raw material.')
        return redirect('raw_material_detail', material_id=material.id)
    
    # Check if material is used in any recipes
    if material.recipe_set.exists():
        messages.error(request, f'Cannot delete "{material.name}" as it is used in product recipes.')
        return redirect('raw_material_detail', material_id=material.id)
    
    if request.method == 'POST':
        material_name = material.name
        material.delete()
        messages.success(request, f'Raw material "{material_name}" deleted successfully.')
        return redirect('raw_material_list')
    
    return render(request, 'juice_app/raw_material/raw_material_delete.html', {'material': material})