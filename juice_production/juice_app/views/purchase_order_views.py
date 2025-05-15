from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.forms import inlineformset_factory
from django.utils import timezone
from ..models import PurchaseOrder, PurchaseOrderItem, Customer, RawMaterial
from django import forms
from ..forms import PurchaseOrderItemForm, PurchaseOrderForm, ReceiveItemForm
import uuid


@login_required
def purchase_order_list(request):
    """Display list of purchase orders."""
    purchase_orders = PurchaseOrder.objects.all().order_by('-order_date')
    return render(request, 'juice_app/purchase/purchase_list.html', {'purchase_orders': purchase_orders})

@login_required
def purchase_order_detail(request, po_id):
    """Display details of a purchase order."""
    po = get_object_or_404(PurchaseOrder, id=po_id)
    items = po.items.all()
    return render(request, 'juice_app/purchase/purchase_detail.html', {'po': po, 'items': items})

@login_required
def purchase_order_new(request):
    """Create a new purchase order."""
    ItemFormSet = inlineformset_factory(
        PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm, extra=3, can_delete=True
    )
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                po = form.save(commit=False)
                po.status = 'draft'
                po.payment_status = 'pending'
                po.created_by = request.user
                
                # Generate PO number
                today = timezone.now().strftime('%Y%m%d')
                count = PurchaseOrder.objects.filter(
                    po_number__startswith=f'PO-{today}').count() + 1
                unique_id = uuid.uuid4().hex[:6].upper()
                po.po_number = f'PO-{today}-{count:03d}-{unique_id}'
                po.save()
                
                # Process items formset
                formset = ItemFormSet(request.POST, instance=po)
                if formset.is_valid():
                    formset.save()
                    messages.success(request, f'Purchase Order {po.po_number} created successfully.')
                    return redirect('purchase_order_detail', po_id=po.id)
        else:
            formset = ItemFormSet(request.POST)
    else:
        form = PurchaseOrderForm(initial={'order_date': timezone.now().date()})
        formset = ItemFormSet()
    
    return render(request, 'juice_app/purchase/purchase_form.html', 
                 {'form': form, 'formset': formset, 'title': 'New Purchase Order'})

@login_required
def purchase_order_edit(request, po_id):
    """Edit an existing purchase order."""
    po = get_object_or_404(PurchaseOrder, id=po_id)
    
    # Only draft POs can be edited
    if po.status != 'draft':
        messages.error(request, 'Only draft purchase orders can be edited.')
        return redirect('purchase_order_detail', po_id=po.id)
    
    ItemFormSet = inlineformset_factory(
        PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm, extra=1, can_delete=True
    )
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = ItemFormSet(request.POST, instance=po)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
                messages.success(request, f'Purchase Order {po.po_number} updated successfully.')
                return redirect('purchase_order_detail', po_id=po.id)
    else:
        form = PurchaseOrderForm(instance=po)
        formset = ItemFormSet(instance=po)
    
    return render(request, 'juice_app/purchase/purchase_form.html', 
                 {'form': form, 'formset': formset, 'title': 'Edit Purchase Order', 'po': po})

@login_required
def purchase_order_receive(request, po_id):
    """Receive items for a purchase order."""
    po = get_object_or_404(PurchaseOrder, id=po_id)
    
    # Only submitted or partially received POs can be received
    if po.status not in ['draft', 'partial']:
        messages.error(request, 'Only draft or partially received purchase orders can be received.')
        return redirect('purchase_order_detail', po_id=po.id)
    
    items = po.items.all()
    
    if request.method == 'POST':
        forms_valid = True
        forms = []
        
        for item in items:
            form_name = f'item_{item.id}'
            form = ReceiveItemForm(request.POST, prefix=form_name)
            forms.append((item, form))
            forms_valid = forms_valid and form.is_valid()
        
        if forms_valid:
            with transaction.atomic():
                for item, form in forms:
                    quantity = form.cleaned_data['quantity_receiving']
                    if quantity > 0:
                        item.update_inventory_on_receipt(quantity)
                
                # Update PO status if needed (handled in update_inventory_on_receipt)
                po.refresh_from_db()
                messages.success(request, f'Items received for Purchase Order {po.po_number}.')
                return redirect('purchase_order_detail', po_id=po.id)
    else:
        forms = [(item, ReceiveItemForm(prefix=f'item_{item.id}')) for item in items]
    
    return render(request, 'juice_app/purchase/purchase_receive.html', 
                 {'po': po, 'forms': forms})

@login_required
def purchase_order_submit(request, po_id):
    """Submit a draft purchase order."""
    po = get_object_or_404(PurchaseOrder, id=po_id)
    
    # Only draft POs can be submitted
    if po.status != 'draft':
        messages.error(request, 'Only draft purchase orders can be submitted.')
        return redirect('purchase_order_detail', po_id=po.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            po.status = 'submitted'
            po.save()
            messages.success(request, f'Purchase Order {po.po_number} submitted successfully.')
            return redirect('purchase_order_detail', po_id=po.id)
    
    return render(request, 'juice_app/purchase/purchase_detail.html', {'po': po})