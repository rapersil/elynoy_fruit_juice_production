from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import *
from django import forms
from django.db.models import Q, Count, Max, Min, F, Sum
from django.db.models.functions import TruncMonth
import json
from ..forms import CustomerForm

@login_required
def customer_list(request):
    """Display list of customers with relevant statistics based on filter."""
    customers = Customer.objects.all().order_by('name')
    
    # Get filter parameters
    filter_type = request.GET.get('type', 'all')
    filter_status = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Apply filters
    if filter_type == 'buyers':
        customers = customers.filter(is_buyer=True)
        total_label = 'Total Buyers'
        active_label = 'Active Buyers'
    elif filter_type == 'suppliers':
        customers = customers.filter(is_supplier=True)
        total_label = 'Total Suppliers'
        active_label = 'Active Suppliers'
    else:
        total_label = 'Total Customers'
        active_label = 'Active Customers'
    
    if filter_status == 'active':
        customers = customers.filter(is_active=True)
    elif filter_status == 'inactive':
        customers = customers.filter(is_active=False)
    
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) | 
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Common statistics
    total_customers = customers.count()
    active_customers = customers.filter(is_active=True).count()
    
    if filter_type == 'all':
        buyers_count = customers.filter(is_buyer=True).count()
        suppliers_count = customers.filter(is_supplier=True).count()
    else:
        buyers_count = None
        suppliers_count = None
    
    # Determine stats type
    stats_type = 'purchase' if filter_type == 'suppliers' else 'sales'
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if stats_type == 'purchase':
        purchases_this_month = PurchaseOrder.objects.filter(
            supplier__in=customers,
            order_date__gte=current_month_start,
            status__in=['submitted', 'partial', 'received']
        )
        total_purchase_amount = purchases_this_month.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        purchases_last_month = PurchaseOrder.objects.filter(
            supplier__in=customers,
            order_date__gte=last_month_start,
            order_date__lt=current_month_start,
            status__in=['submitted', 'partial', 'received']
        )
        last_month_purchases = purchases_last_month.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        purchase_growth = 0
        if last_month_purchases > 0:
            purchase_growth = ((total_purchase_amount - last_month_purchases) / last_month_purchases) * 100
        
        ninety_days_ago = timezone.now().date() - timedelta(days=90)
        top_suppliers = PurchaseOrder.objects.filter(
            supplier__in=customers,
            order_date__gte=ninety_days_ago,
            status__in=['submitted', 'partial', 'received']
        ).values(
            'supplier__id', 
            'supplier__name'
        ).annotate(
            total_purchases=Sum('total_amount'),
            po_count=Count('id')
        ).order_by('-total_purchases')[:5]
        
        recent_suppliers = PurchaseOrder.objects.filter(
            supplier__in=customers,
            status__in=['submitted', 'partial', 'received']
        ).values(
            'supplier__id', 
            'supplier__name'
        ).annotate(
            last_purchase=Max('order_date')
        ).order_by('-last_purchase')[:5]
        
        total_sales_amount = None
        sales_growth = None
        top_customers = []
        recent_customers = []
    else:
        sales_customers = customers if filter_type == 'buyers' else Customer.objects.filter(is_buyer=True)
        sales_this_month = Sale.objects.filter(
            customer__in=sales_customers,
            sale_date__gte=current_month_start,
            status__in=['confirmed', 'shipped', 'delivered']
        )
        total_sales_amount = sales_this_month.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        sales_last_month = Sale.objects.filter(
            customer__in=sales_customers,
            sale_date__gte=last_month_start,
            sale_date__lt=current_month_start,
            status__in=['confirmed', 'shipped', 'delivered']
        )
        last_month_sales = sales_last_month.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        sales_growth = 0
        if last_month_sales > 0:
            sales_growth = ((total_sales_amount - last_month_sales) / last_month_sales) * 100
        
        ninety_days_ago = timezone.now().date() - timedelta(days=90)
        top_customers = Sale.objects.filter(
            customer__in=sales_customers,
            sale_date__gte=ninety_days_ago,
            status__in=['confirmed', 'shipped', 'delivered']
        ).values(
            'customer__id', 
            'customer__name'
        ).annotate(
            total_sales=Sum('total_amount'),
            sale_count=Count('id')
        ).order_by('-total_sales')[:5]
        
        recent_customers = Sale.objects.filter(
            customer__in=sales_customers,
            status__in=['confirmed', 'shipped', 'delivered']
        ).values(
            'customer__id', 
            'customer__name'
        ).annotate(
            last_purchase=Max('sale_date')
        ).order_by('-last_purchase')[:5]
        
        total_purchase_amount = None
        purchase_growth = None
        top_suppliers = []
        recent_suppliers = []
    
    context = {
        'customers': customers,
        'total_customers': total_customers,
        'buyers_count': buyers_count,
        'suppliers_count': suppliers_count,
        'active_customers': active_customers,
        'total_label': total_label,
        'active_label': active_label,
        'stats_type': stats_type,
        'total_sales_amount': total_sales_amount,
        'sales_growth': sales_growth,
        'total_purchase_amount': total_purchase_amount,
        'purchase_growth': purchase_growth,
        'top_customers': top_customers,
        'recent_customers': recent_customers,
        'top_suppliers': top_suppliers,
        'recent_suppliers': recent_suppliers,
        'filter_type': filter_type,
        'filter*filter_status': filter_status,
        'search_query': search_query,
    }
    
    return render(request, 'juice_app/customer/customer_list.html', context)

@login_required
def supplier_list(request):
    """Display list of suppliers (customers who are suppliers)."""
    suppliers = Customer.objects.filter(is_supplier=True).order_by('name')
    
    # For recent purchase orders
    recent_purchase_orders = PurchaseOrder.objects.filter(
        supplier__is_supplier=True
    ).order_by('-order_date')[:5]
    
    # Create a list of suppliers with additional material data
    materials_by_supplier = []
    for supplier in suppliers:
        materials = RawMaterial.objects.filter(supplier=supplier)
        total_value = sum(material.quantity_in_stock * material.unit_cost for material in materials)
        
        materials_by_supplier.append({
            'id': supplier.id,
            'name': supplier.name,
            'material_count': materials.count(),
            'total_value': total_value
        })
    
    context = {
        'suppliers': suppliers,
        'materials_by_supplier': materials_by_supplier,
        'recent_purchase_orders': recent_purchase_orders
    }
    
    return render(request, 'juice_app/supplier/supplier_list.html', context)

@login_required
def customer_detail(request, customer_id):
    """Display comprehensive details of a customer with enhanced analytics."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get related orders if they're a supplier
    purchase_orders = None
    if customer.is_supplier:
        purchase_orders = customer.purchaseorder_set.all().order_by('-order_date')[:5]
    
    # Get related sales if they're a buyer
    sales = None
    sales_count = 0
    total_sales = 0
    avg_order_value = 0
    first_purchase_date = None
    last_purchase_date = None
    purchase_frequency = None
    
    if customer.is_buyer:
        sales = customer.sale_set.filter(status__in=['confirmed', 'shipped', 'delivered']).order_by('-sale_date')
        sales_count = sales.count()
        
        # Calculate financial metrics
        total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        avg_order_value = total_sales / sales_count if sales_count > 0 else 0
        
        # Get first and last purchase dates
        date_metrics = sales.aggregate(
            first_date=Min('sale_date'),
            last_date=Max('sale_date')
        )
        first_purchase_date = date_metrics['first_date']
        last_purchase_date = date_metrics['last_date']
        
        # Calculate purchase frequency (average days between orders)
        if sales_count > 1 and first_purchase_date and last_purchase_date:
            days_as_customer = (last_purchase_date - first_purchase_date).days
            purchase_frequency = days_as_customer / (sales_count - 1) if days_as_customer > 0 else None
    
    # Credit information and status
    paid_amount = customer.sale_set.filter(
        payment_status__in=['paid', 'partial']
    ).aggregate(paid=Sum('total_amount'))['paid'] or 0
    
    credit_used = max(0, total_sales - paid_amount)
    credit_available = max(0, customer.credit_limit - credit_used) if customer.credit_limit else 0
    credit_percent = (credit_used / customer.credit_limit * 100) if customer.credit_limit and customer.credit_limit > 0 else 0
    
    # Get payment history
    payment_history = Payment.objects.filter(
        sale__customer=customer
    ).order_by('-payment_date')[:5]
    
    payment_totals = payment_history.aggregate(
        total_paid=Sum('amount')
    )['total_paid'] or 0
    
    # Get payment method breakdown
    payment_methods = Payment.objects.filter(
        sale__customer=customer
    ).values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Get purchased products with metrics
    purchased_products = []
    if customer.is_buyer:
        product_data = SaleItem.objects.filter(
            sale__customer=customer,
            sale__status__in=['confirmed', 'shipped', 'delivered']
        ).values(
            'product__id',
            'product__name',
            'product__bottle__size'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_value=Sum('total_price'),
            last_purchase_date=Max('sale__sale_date'),
            purchase_count=Count('sale__id', distinct=True)
        ).order_by('-total_value')[:10]
        
        purchased_products = list(product_data)
    
    # Seasonal purchase analysis
    monthly_sales = {}
    if customer.is_buyer and sales_count > 0:
        monthly_data = sales.annotate(
            month=TruncMonth('sale_date')
        ).values('month').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('month')
        
        # Convert to lists for chart
        months = [item['month'].strftime('%b %Y') for item in monthly_data]
        monthly_amounts = [float(item['total']) for item in monthly_data]
        monthly_counts = [item['count'] for item in monthly_data]
        
        monthly_sales = {
            'months': json.dumps(months),
            'amounts': json.dumps(monthly_amounts),
            'counts': json.dumps(monthly_counts)
        }
    
    # Customer lifetime value (simplified)
    customer_lifetime_value = total_sales
    if sales_count > 0 and first_purchase_date:
        today = timezone.now().date()
        days_as_customer = (today - first_purchase_date).days if first_purchase_date else 0
        years_as_customer = days_as_customer / 365.0
        if years_as_customer > 0:
            annual_value = float(total_sales) / years_as_customer
            customer_lifetime_value = annual_value * 3  # Projected for 3 years
    
    context = {
        'customer': customer,
        'purchase_orders': purchase_orders,
        'sales': sales[:10] if sales else None,  # Limit to most recent 10
        'sales_count': sales_count,
        'total_sales': total_sales,
        'avg_order_value': avg_order_value,
        'first_purchase_date': first_purchase_date,
        'last_purchase_date': last_purchase_date,
        'purchase_frequency': purchase_frequency,
        'credit_used': credit_used,
        'credit_available': credit_available,
        'credit_percent': credit_percent,
        'payment_history': payment_history,
        'payment_totals': payment_totals,
        'payment_methods': payment_methods,
        'purchased_products': purchased_products,
        'monthly_sales': monthly_sales,
        'customer_lifetime_value': customer_lifetime_value,
    }
    
    return render(request, 'juice_app/customer/customer_detail.html', context)

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