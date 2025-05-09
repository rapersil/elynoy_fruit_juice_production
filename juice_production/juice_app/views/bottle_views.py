from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from ..models import Bottle, Product
from ..forms import BottleForm

@login_required
def bottle_list(request):
    """Display list of bottle sizes with filtering functionality."""
    # Get filter parameters
    filter_status = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Start with all bottles
    bottles = Bottle.objects.all()
    
    # Apply filters
    if filter_status == 'active':
        bottles = bottles.filter(is_active=True)
    elif filter_status == 'inactive':
        bottles = bottles.filter(is_active=False)
    
    # Apply search if provided
    if search_query:
        bottles = bottles.filter(size__icontains=search_query)
    
    # Annotate with product count
    bottles = bottles.annotate(product_count=Count('product'))
    
    # Order by size
    bottles = bottles.order_by('size')
    
    # Get statistics for summary
    total_bottles = bottles.count()
    active_bottles = bottles.filter(is_active=True).count()
    total_products = Product.objects.filter(bottle__in=bottles).count()
    
    context = {
        'bottles': bottles,
        'total_bottles': total_bottles,
        'active_bottles': active_bottles,
        'total_products': total_products,
        'filter_status': filter_status,
        'search_query': search_query,
    }
    
    return render(request, 'juice_app/bottle/bottle_list.html', context)

@login_required
def bottle_detail(request, bottle_id):
    """Display details of a bottle size."""
    bottle = get_object_or_404(Bottle, id=bottle_id)
    products = bottle.product_set.all()
    
    # Check if user can edit/delete this bottle
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = hasattr(bottle, 'created_by') and bottle.created_by == request.user
    can_edit = is_admin or is_creator
    
    context = {
        'bottle': bottle,
        'products': products,
        'can_edit': can_edit
    }
    
    return render(request, 'juice_app/bottle/bottle_detail.html', context)

@login_required
def bottle_new(request):
    """Create a new bottle size."""
    if request.method == 'POST':
        form = BottleForm(request.POST)
        if form.is_valid():
            bottle = form.save(commit=False)
            if hasattr(bottle, 'created_by'):
                bottle.created_by = request.user
            bottle.save()
            messages.success(request, f'Bottle size "{bottle.size}" created successfully.')
            return redirect('bottle_list')
    else:
        form = BottleForm()
    
    return render(request, 'juice_app/bottle/bottle_form.html', 
                 {'form': form, 'title': 'New Bottle Size'})

@login_required
def bottle_edit(request, bottle_id):
    """Edit an existing bottle size with permission checks."""
    bottle = get_object_or_404(Bottle, id=bottle_id)
    
    # Permission check: only admin/superadmin or creator can edit
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = hasattr(bottle, 'created_by') and bottle.created_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to edit this bottle size.')
        return redirect('bottle_detail', bottle_id=bottle.id)
    
    if request.method == 'POST':
        form = BottleForm(request.POST, instance=bottle)
        if form.is_valid():
            form.save()
            messages.success(request, f'Bottle size "{bottle.size}" updated successfully.')
            return redirect('bottle_detail', bottle_id=bottle.id)
    else:
        form = BottleForm(instance=bottle)
    
    return render(request, 'juice_app/bottle/bottle_form.html', 
                 {'form': form, 'title': 'Edit Bottle Size', 'bottle': bottle})

@login_required
def bottle_delete(request, bottle_id):
    """Delete a bottle size with permission checks."""
    bottle = get_object_or_404(Bottle, id=bottle_id)
    
    # Permission check: only admin/superadmin or creator can delete
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = hasattr(bottle, 'created_by') and bottle.created_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to delete this bottle size.')
        return redirect('bottle_detail', bottle_id=bottle.id)
    
    # Check if bottle is used in any products
    if bottle.product_set.exists():
        messages.error(request, f'Cannot delete "{bottle.size}" as it is used in products.')
        return redirect('bottle_detail', bottle_id=bottle.id)
    
    if request.method == 'POST':
        bottle_size = bottle.size
        bottle.delete()
        messages.success(request, f'Bottle size "{bottle_size}" deleted successfully.')
        return redirect('bottle_list')
    
    return render(request, 'juice_app/bottle/bottle_delete.html', {'bottle': bottle})