from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.forms import inlineformset_factory
from django.db.models import Q, Sum, Count
from juice_app.models import (
    ProductionBatch, MaterialUsage, Product, RawMaterial
)
from ..forms import ProductionBatchForm, MaterialUsageForm
from django import forms

@login_required
def production_list(request):
    """Display list of production batches with filtering and search functionality."""
    # Get all products for filter dropdown
    all_products = Product.objects.filter(is_active=True).order_by('name')
    
    # Initialize filter variables
    filter_status = request.GET.get('status', 'all')
    filter_product = request.GET.get('product', 'all')
    search_query = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Start with all batches
    batches = ProductionBatch.objects.all()
    
    # Apply status filter
    if filter_status != 'all':
        batches = batches.filter(status=filter_status)
    
    # Apply product filter
    if filter_product != 'all':
        batches = batches.filter(product_id=filter_product)
    
    # Apply search filter (search in batch number and product name)
    if search_query:
        batches = batches.filter(
            Q(batch_number__icontains=search_query) | 
            Q(product__name__icontains=search_query)
        )
    
    # Apply date range filter
    if start_date and end_date:
        try:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            batches = batches.filter(production_date__range=[start_date_obj, end_date_obj])
        except ValueError:
            # Handle invalid date format
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
    
    # Calculate metrics for dashboard cards
    total_batches = batches.count()
    completed_batches = batches.filter(status='completed').count()
    in_progress_batches = batches.filter(status='in_progress').count()
    
    # Calculate efficiency percentage
    efficiency_percentage = 0
    completed_with_quantities = batches.filter(
        status='completed',
        planned_quantity__gt=0,
        actual_quantity_produced__isnull=False
    )
    
    if completed_with_quantities.exists():
        total_planned = completed_with_quantities.aggregate(Sum('planned_quantity'))['planned_quantity__sum'] or 0
        total_actual = completed_with_quantities.aggregate(Sum('actual_quantity_produced'))['actual_quantity_produced__sum'] or 0
        
        if total_planned > 0:
            efficiency_percentage = (total_actual / total_planned) * 100
    
    # Order by most recent production date first
    batches = batches.order_by('-production_date')
    
    context = {
        'batches': batches,
        'all_products': all_products,
        'filter_status': filter_status,
        'filter_product': filter_product,
        'search_query': search_query,
        'start_date': start_date,
        'end_date': end_date,
        'total_batches': total_batches,
        'completed_batches': completed_batches,
        'in_progress_batches': in_progress_batches,
        'efficiency_percentage': efficiency_percentage,
    }
    
    return render(request, 'juice_app/production/production_list.html', context)
@login_required
def production_detail(request, batch_id):
    """Display details of a production batch."""
    batch = get_object_or_404(ProductionBatch, id=batch_id)
    print(batch_id)
    material_usages = batch.material_usages.all().select_related('raw_material')
    
    # Check if user can edit/cancel this batch
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = batch.produced_by == request.user
    can_manage = is_admin or is_creator
    
    # Determine available actions based on batch status
    can_start = batch.status == 'planned' and can_manage
    can_complete = batch.status == 'in_progress' and can_manage
    can_cancel = batch.status not in ['completed', 'cancelled'] and can_manage
    
    context = {
        'batch': batch,
        'material_usages': material_usages,
        'can_manage': can_manage,
        'can_start': can_start,
        'can_complete': can_complete,
        'can_cancel': can_cancel,
    }
    
    return render(request, 'juice_app/production/production_detail.html', context)

@login_required
def production_new(request):
    """Create a new production batch with automatic batch number generation."""
    # Pre-select product if specified in query parameter
    initial_data = {}
    product_id = request.GET.get('product')
    if product_id and product_id.isdigit():
        try:
            product = Product.objects.get(id=int(product_id))
            initial_data['product'] = product
        except Product.DoesNotExist:
            pass
    
    initial_data['production_date'] = timezone.now().date()
    
    if request.method == 'POST':
        form = ProductionBatchForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Create the batch
                batch = form.save(commit=False)
                batch.status = 'planned'
                batch.produced_by = request.user
                
                # Generate batch number if not provided
                today = timezone.now().strftime('%Y-%m-%d')
                count = ProductionBatch.objects.filter(
                    batch_number__startswith=f'BATCH-{today}').count() + 1
                batch.batch_number = f'BATCH-{today}-{count:03d}'
                
                batch.save()
                
                # Create material usage records based on recipe
                product = batch.product
                for ingredient in product.ingredients.all():
                    MaterialUsage.objects.create(
                        batch=batch,
                        raw_material=ingredient.raw_material,
                        planned_quantity=ingredient.quantity_required * batch.planned_quantity,
                    )
                
                messages.success(request, f'Production batch {batch.batch_number} created successfully.')
                return redirect('production_detail', batch_id=batch.id)
    else:
        form = ProductionBatchForm(initial=initial_data)
    
    return render(request, 'juice_app/production/production_form.html', 
                 {'form': form, 'title': 'New Production Batch'})

@login_required
def production_start(request, batch_id):
    """Start a production batch with permission checks."""
    batch = get_object_or_404(ProductionBatch, id=batch_id)
    
    # Permission check: only admin/superadmin or creator can start
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = batch.produced_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to start this production batch.')
        return redirect('production_detail', batch_id=batch.id)
    
    if batch.status != 'planned':
        messages.error(request, 'Only planned batches can be started.')
        return redirect('production_detail', batch_id=batch.id)
    
    # Check if there are sufficient materials
    insufficient_materials = []
    for usage in batch.material_usages.all():
        if usage.raw_material.quantity_in_stock < usage.planned_quantity:
            insufficient_materials.append(
                f"{usage.raw_material.name}: Need {usage.planned_quantity}, Have {usage.raw_material.quantity_in_stock}"
            )
    
    if insufficient_materials:
        messages.error(request, 'Insufficient materials to start production: ' + '; '.join(insufficient_materials))
        return redirect('production_detail', batch_id=batch.id)
    
    # Start the batch
    batch.status = 'in_progress'
    batch.save()
    messages.success(request, f'Production batch {batch.batch_number} started.')
    return redirect('production_detail', batch_id=batch.id)

@login_required
def production_complete(request, batch_id):
    """Complete a production batch."""
    batch = get_object_or_404(ProductionBatch, id=batch_id)
    
    if batch.status != 'in_progress':
        messages.error(request, 'Only in-progress batches can be completed.')
        return redirect('production_detail', batch_id=batch.id)
    
    MaterialUsageFormSet = inlineformset_factory(
        ProductionBatch, MaterialUsage, 
        form=MaterialUsageForm, extra=0
    )
    
    if request.method == 'POST':
        # Debug output
        print("POST data:", request.POST)
        
        form = ProductionBatchForm(request.POST, instance=batch)
        formset = MaterialUsageFormSet(request.POST, instance=batch)
        
        # Debug output
        print("Form fields:", form.fields.keys())
        print("Form errors:", form.errors)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Update the batch
                batch = form.save(commit=False)
                batch.status = 'completed'
                batch.completion_date = timezone.now().date()
                batch.save()
                
                # Save material usages
                formset.save()
                
                messages.success(request, f'Production batch {batch.batch_number} completed successfully.')
                return redirect('production_detail', batch_id=batch.id)
    else:
        form = ProductionBatchForm(instance=batch)
        # Ensure these fields are explicitly available
        if 'actual_quantity_produced' not in form.fields:
            form.fields['actual_quantity_produced'] = forms.DecimalField(
                max_digits=10, decimal_places=2, min_value=0,
                initial=batch.planned_quantity
            )
        if 'quality_check_passed' not in form.fields:
            form.fields['quality_check_passed'] = forms.BooleanField(required=False, initial=True)
            
        formset = MaterialUsageFormSet(instance=batch)
    
    return render(request, 'juice_app/production/production_complete_form.html', 
                {'form': form, 'formset': formset, 'batch': batch})

@login_required
def production_cancel(request, batch_id):
    """Cancel a production batch with permission checks."""
    batch = get_object_or_404(ProductionBatch, id=batch_id)
    
    # Permission check: only admin/superadmin or creator can cancel
    is_admin = request.user.profile.role in ['admin', 'superadmin']
    is_creator = batch.produced_by == request.user
    
    if not (is_admin or is_creator):
        messages.error(request, 'You do not have permission to cancel this production batch.')
        return redirect('production_detail', batch_id=batch.id)
    
    if batch.status == 'completed':
        messages.error(request, 'Completed batches cannot be cancelled.')
        return redirect('production_detail', batch_id=batch.id)
    
    if request.method == 'POST':
        batch.status = 'cancelled'
        batch.save()
        messages.success(request, f'Production batch {batch.batch_number} cancelled.')
        return redirect('production_list')
    
    return render(request, 'juice_app/production/production_confirm_cancel.html', {'batch': batch})





@login_required
def production_edit(request, batch_id):
    """Edit an existing production batch."""
    batch = get_object_or_404(ProductionBatch, id=batch_id)
    
    # Check permissions - only batch creator, admins, or superadmins can edit
    if batch.produced_by != request.user and request.user.profile.role not in ['admin', 'superadmin']:
        messages.error(request, 'You do not have permission to edit this batch.')
        return redirect('production_detail', batch_id=batch.id)
    
    # Only planned batches can be edited
    if batch.status != 'planned':
        messages.error(request, 'Only planned batches can be edited.')
        return redirect('production_detail', batch_id=batch.id)
    
    if request.method == 'POST':
        form = ProductionBatchForm(request.POST, instance=batch, batch_status=batch.status)
        if form.is_valid():
            with transaction.atomic():
                # Update the batch
                updated_batch = form.save()
                
                # Delete existing material usages
                MaterialUsage.objects.filter(batch=batch).delete()
                
                # Create new material usages based on updated product and quantity
                product = updated_batch.product
                for ingredient in product.ingredients.all():
                    MaterialUsage.objects.create(
                        batch=updated_batch,
                        raw_material=ingredient.raw_material,
                        planned_quantity=ingredient.quantity_required * updated_batch.planned_quantity,
                    )
                
                messages.success(request, f'Production batch {updated_batch.batch_number} updated successfully.')
                return redirect('production_detail', batch_id=updated_batch.id)
    else:
        form = ProductionBatchForm(instance=batch, batch_status=batch.status)
    
    return render(request, 'juice_app/production/production_form.html', 
                {'form': form, 'batch': batch, 'title': 'Edit Production Batch'})