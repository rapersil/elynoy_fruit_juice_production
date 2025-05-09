from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Customer
from django import forms
from django.db.models import Q

from ..forms import CustomerForm

@login_required
def customer_list(request):
    """Display list of customers (both buyers and suppliers)."""
    customers = Customer.objects.all().order_by('name')
    return render(request, 'juice_app/customer/customer_list.html', {'customers': customers})

@login_required
def supplier_list(request):
    """Display list of suppliers (customers who are suppliers)."""
    suppliers = Customer.objects.filter(is_supplier=True).order_by('name')
    return render(request, 'juice_app/supplier/supplier_list.html', {'suppliers': suppliers})

@login_required
def customer_detail(request, customer_id):
    """Display details of a customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    # Get related orders if they're a supplier
    purchase_orders = None
    if customer.is_supplier:
        purchase_orders = customer.purchaseorder_set.all().order_by('-order_date')[:5]
    
    # Get related sales if they're a buyer
    sales = None
    if customer.is_buyer:
        sales = customer.sale_set.all().order_by('-sale_date')[:5]
    
    return render(request, 'juice_app/customer/customer_detail.html', 
                 {'customer': customer, 'purchase_orders': purchase_orders, 'sales': sales})

@login_required
def customer_new(request):
    """Create a new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" created successfully.')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    
    return render(request, 'juice_app/customer/customer_form.html', 
                 {'form': form, 'title': 'New Customer'})

@login_required
def customer_edit(request, customer_id):
    """Edit an existing customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully.')
            return redirect('customer_detail', customer_id=customer.id)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'juice_app/customer/customer_form.html', 
                 {'form': form, 'title': 'Edit Customer', 'customer': customer})