from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Sum
from django.forms import inlineformset_factory
from django.utils import timezone
from ..models import Sale, SaleItem, Customer, Product, Payment
from django import forms
from ..forms import SaleItemForm, SaleForm, PaymentForm


@login_required
def sale_list(request):
    """Display list of sales."""
    sales = Sale.objects.all().order_by('-sale_date')
    return render(request, 'juice_app/sale/sale_list.html', {'sales': sales})

@login_required
def sale_detail(request, sale_id):
    """Display details of a sale."""
    sale = get_object_or_404(Sale, id=sale_id)
    items = sale.items.all()
    
    # Process batch numbers for each item
    for item in items:
        if item.batch_numbers:
            item.batch_list = [batch.strip() for batch in item.batch_numbers.split(',')]
        else:
            item.batch_list = []
    
    return render(request, 'juice_app/sale/sale_detail.html', {'sale': sale, 'items': items})

@login_required
def sale_new(request):
    """Create a new sale."""
    ItemFormSet = inlineformset_factory(
        Sale, SaleItem, form=SaleItemForm, extra=3, can_delete=True
    )
    
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                sale = form.save(commit=False)
                sale.status = 'draft'
                sale.payment_status = 'pending'
                sale.created_by = request.user
                
                # Generate invoice number
                today = timezone.now().strftime('%Y%m%d')
                count = Sale.objects.filter(
                    invoice_number__startswith=f'INV-{today}').count() + 1
                sale.invoice_number = f'INV-{today}-{count:03d}'
                
                sale.save()
                
                # Process items formset
                formset = ItemFormSet(request.POST, instance=sale)
                if formset.is_valid():
                    # Check stock before saving
                    for form in formset:
                        if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                            product = form.cleaned_data.get('product')
                            quantity = form.cleaned_data.get('quantity')
                            if product and quantity and product.stock_quantity < quantity:
                                form.add_error('quantity', f'Insufficient stock. Available: {product.stock_quantity}')
                                return render(request, 'juice_app/sale/sale_form.html', 
                                            {'form': form, 'formset': formset, 'title': 'New Sale'})
                    
                    formset.save()
                    messages.success(request, f'Sale {sale.invoice_number} created successfully.')
                    return redirect('sale_detail', sale_id=sale.id)
        else:
            formset = ItemFormSet(request.POST)
    else:
        form = SaleForm(initial={'sale_date': timezone.now().date()})
        formset = ItemFormSet()
    
    return render(request, 'juice_app/sale/sale_form.html', 
                 {'form': form, 'formset': formset, 'title': 'New Sale'})

@login_required
def sale_edit(request, sale_id):
    """Edit an existing sale."""
    sale = get_object_or_404(Sale, id=sale_id)
    
    # Only draft sales can be edited
    if sale.status != 'draft':
        messages.error(request, 'Only draft sales can be edited.')
        return redirect('sale_detail', sale_id=sale.id)
    
    ItemFormSet = inlineformset_factory(
        Sale, SaleItem, form=SaleItemForm, extra=1, can_delete=True
    )
    
    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        formset = ItemFormSet(request.POST, instance=sale)
        
        if form.is_valid() and formset.is_valid():
            # Check stock before saving
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    product = form.cleaned_data.get('product')
                    quantity = form.cleaned_data.get('quantity')
                    
                    # Get original quantity if this is an existing item
                    original_quantity = 0
                    if form.instance.pk:
                        original_quantity = SaleItem.objects.get(pk=form.instance.pk).quantity
                    
                    # Check if we have enough stock for the new quantity
                    net_increase = quantity - original_quantity
                    if product and net_increase > 0 and product.stock_quantity < net_increase:
                        form.add_error('quantity', f'Insufficient stock. Available: {product.stock_quantity}')
                        return render(request, 'juice_app/sale/sale_form.html', 
                                    {'form': form, 'formset': formset, 'title': 'Edit Sale', 'sale': sale})
            
            with transaction.atomic():
                form.save()
                formset.save()
                messages.success(request, f'Sale {sale.invoice_number} updated successfully.')
                return redirect('sale_detail', sale_id=sale.id)
    else:
        form = SaleForm(instance=sale)
        formset = ItemFormSet(instance=sale)
    
    return render(request, 'juice_app/sale/sale_form.html', 
                 {'form': form, 'formset': formset, 'title': 'Edit Sale', 'sale': sale})

@login_required
def sale_confirm(request, sale_id):
    """Confirm a sale and update inventory."""
    sale = get_object_or_404(Sale, id=sale_id)
    
    # Only draft sales can be confirmed
    if sale.status != 'draft':
        messages.error(request, 'Only draft sales can be confirmed.')
        return redirect('sale_detail', sale_id=sale.id)
    
    # Check if there are any items
    if not sale.items.exists():
        messages.error(request, 'Cannot confirm a sale with no items.')
        return redirect('sale_detail', sale_id=sale.id)
    
    # Check stock levels again
    insufficient_stock = []
    for item in sale.items.all():
        if item.product.stock_quantity < item.quantity:
            insufficient_stock.append(
                f"{item.product.name}: Need {item.quantity}, Have {item.product.stock_quantity}"
            )
    
    if insufficient_stock:
        messages.error(request, 'Insufficient stock to confirm sale: ' + '; '.join(insufficient_stock))
        return redirect('sale_detail', sale_id=sale.id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Update sale status
            sale.status = 'confirmed'
            sale.save()
            
            # The signal will handle updating product stock
            
            messages.success(request, f'Sale {sale.invoice_number} confirmed successfully.')
            return redirect('sale_detail', sale_id=sale.id)
    
    return render(request, 'juice_app/sale/sale_confirm.html', {'sale': sale})



@login_required
def sale_receipt(request, sale_id):
    """Generate a printable receipt for a sale."""
    sale = get_object_or_404(Sale, id=sale_id)
    items = sale.items.all()
    
    # Calculate any additional metrics needed for receipt
    subtotal = sum(item.quantity * item.unit_price for item in items)
    tax_rate = 0.05  # 5% tax rate (this could be made configurable)
    tax_amount = float(subtotal) * tax_rate
    
    context = {
        'sale': sale,
        'items': items,
        'subtotal': subtotal,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'company_name': 'Fruit Juice Production Ltd',  # Can be pulled from settings
        'company_address': '123 Production Lane, Accra, Ghana',
        'company_phone': '+233 12 345 6789',
        'receipt_date': timezone.now(),
    }
    
    return render(request, 'juice_app/sale/sale_receipt.html', context)



@login_required
def sales_dashboard(request):
    """Display a comprehensive sales dashboard."""
    # Get date range parameters
    today = timezone.now().date()
    
    # Default to current month if not specified
    start_date = request.GET.get('start_date', (today.replace(day=1)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date).date()
    except (ValueError, TypeError):
        start_date = today.replace(day=1)  # First day of current month
        end_date = today
    
    # Filter sales by date range
    sales = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    )
    
    # Calculate summary metrics
    sales_agg = sales.aggregate(
        total=models.Sum('total_amount'),
        count=models.Count('id')
    )
    total_sales = sales_agg['total'] or 0
    total_count = sales_agg['count'] or 0
    avg_sale = total_sales / total_count if total_count > 0 else 0
    
    # Sales by status
    sales_by_status = sales.values('status').annotate(
        count=models.Count('id'),
        total=models.Sum('total_amount')
    ).order_by('status')
    
    # Sales by payment status
    sales_by_payment = sales.values('payment_status').annotate(
        count=models.Count('id'),
        total=models.Sum('total_amount')
    ).order_by('payment_status')
    
    # Top selling products
    top_products = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).values('product__name').annotate(
        quantity=models.Sum('quantity'),
        revenue=models.Sum('total_price'),
        avg_price=models.Avg('unit_price')
    ).order_by('-revenue')[:10]
    
    # Calculate total products sold
    total_products_sold = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    # Daily sales trend - Handle SQLite compatibility issues
    # Instead of using TruncDate, we'll extract the date part manually
    sales_by_day = []
    # First get all sales with their dates
    all_sales = list(sales.values('id', 'sale_date', 'total_amount'))
    
    # Group by date
    date_groups = {}
    for sale in all_sales:
        # Extract just the date part as string
        sale_date = sale['sale_date'].strftime('%Y-%m-%d')
        if sale_date not in date_groups:
            date_groups[sale_date] = {'total': 0, 'count': 0}
        
        date_groups[sale_date]['total'] += float(sale['total_amount'])
        date_groups[sale_date]['count'] += 1
    
    # Sort dates
    sorted_dates = sorted(date_groups.keys())
    
    # Prepare data for charts
    days = sorted_dates
    daily_totals = [date_groups[date]['total'] for date in sorted_dates]
    daily_counts = [date_groups[date]['count'] for date in sorted_dates]
    
    # Top customers
    top_customers = sales.values('customer__name', 'customer__id').annotate(
        total_spend=models.Sum('total_amount'),
        order_count=models.Count('id'),
        avg_order=models.ExpressionWrapper(
            models.Sum('total_amount') / models.Count('id'),
            output_field=models.DecimalField()
        )
    ).order_by('-total_spend')[:10]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'total_count': total_count,
        'avg_sale': avg_sale,
        'sales_by_status': sales_by_status,
        'sales_by_payment': sales_by_payment,
        'top_products': top_products,
        'top_customers': top_customers,
        'days': days,
        'daily_totals': daily_totals,
        'daily_counts': daily_counts,
        'total_products_sold': total_products_sold,
    }
    
    return render(request, 'juice_app/sale/sale_dashboard.html', context)



@login_required
def top_customers_analysis(request):
    """Provide detailed analysis of top customers."""
    # Get date range parameters
    today = timezone.now().date()
    
    # Default to current month if not specified
    start_date = request.GET.get('start_date', (today.replace(day=1)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date).date()
    except (ValueError, TypeError):
        start_date = today.replace(day=1)  # First day of current month
        end_date = today
    
    # Top customers by revenue
    top_customers = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    ).values('customer__name', 'customer__id').annotate(
        total_spend=models.Sum('total_amount'),
        order_count=models.Count('id'),
        avg_order=models.Avg('total_amount'),
        last_purchase=models.Max('sale_date')
    ).order_by('-total_spend')[:20]
    
    # Get total revenue for the period
    total_revenue = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    # Calculate percentage of total revenue for each customer
    for customer in top_customers:
        customer['revenue_percentage'] = (customer['total_spend'] / total_revenue) * 100 if total_revenue > 0 else 0
    
    # Customer purchase frequency
    # Group customers by number of orders
    frequency_distribution = {}
    
    for customer in top_customers:
        order_count = customer['order_count']
        if order_count in frequency_distribution:
            frequency_distribution[order_count] += 1
        else:
            frequency_distribution[order_count] = 1
    
    # Convert to lists for Chart.js
    frequency_labels = list(frequency_distribution.keys())
    frequency_values = list(frequency_distribution.values())
    
    # What customers are buying
    customer_products = {}
    
    for customer in top_customers[:5]:
        products = SaleItem.objects.filter(
            sale__customer_id=customer['customer__id'],
            sale__sale_date__range=[start_date, end_date],
            sale__status__in=['confirmed', 'shipped', 'delivered']
        ).values('product__name').annotate(
            quantity=models.Sum('quantity'),
            total=models.Sum('total_price')
        ).order_by('-total')[:5]
        
        customer_products[customer['customer__name']] = list(products)
    
    # Get customer names and total spend for chart
    customer_names = [c['customer__name'] for c in top_customers[:10]]
    customer_spend = [float(c['total_spend']) for c in top_customers[:10]]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'top_customers': top_customers,
        'total_revenue': total_revenue,
        'customer_products': customer_products,
        'frequency_labels': frequency_labels,
        'frequency_values': frequency_values,
        'customer_names': customer_names,
        'customer_spend': customer_spend,
    }
    
    return render(request, 'juice_app/sale/sale_top_customers_analysis.html', context)


# Sale payments views 

@login_required
def payment_list(request, sale_id):
    """Display list of payments for a sale."""
    sale = get_object_or_404(Sale, id=sale_id)
    payments = sale.payments.all().order_by('-payment_date')
    
    # Calculate total paid and balance
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = sale.total_amount - total_paid
    
    context = {
        'sale': sale,
        'payments': payments,
        'total_paid': total_paid,
        'balance': balance,
    }
    
    return render(request, 'juice_app/sale/sale_payment_list.html', context)

@login_required
def payment_add(request, sale_id):
    """Add a new payment for a sale."""
    sale = get_object_or_404(Sale, id=sale_id)
    
    # Calculate remaining balance
    total_paid = sale.payments.aggregate(Sum('amount'))['amount__sum'] or 0
    balance = sale.total_amount - total_paid
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale = sale
            payment.received_by = request.user
            
            # Validate that payment amount doesn't exceed balance
            if payment.amount > balance:
                form.add_error('amount', f'Payment amount exceeds remaining balance (GHS{balance}).')
            else:
                payment.save()
                messages.success(request, f'Payment of GHS{payment.amount} recorded successfully.')
                return redirect('payment_list', sale_id=sale.id)
    else:
        # Pre-fill the amount with the remaining balance
        print('not saved')
        form = PaymentForm(initial={'amount': balance, 'payment_date': timezone.now().date()})
        
    
    context = {
        'form': form,
        'sale': sale,
        'balance': balance,
    }
    
    return render(request, 'juice_app/sale/sale_payment_form.html', context)



@login_required
def payment_detail(request, sale_id, payment_id):
    """Display payment details."""
    sale = get_object_or_404(Sale, id=sale_id)
    payment = get_object_or_404(Payment, id=payment_id, sale=sale)
    
    context = {
        'sale': sale,
        'payment': payment,
    }
    
    return render(request, 'juice_app/sale/sale_payment_detail.html', context)

@login_required
def payment_edit(request, sale_id, payment_id):
    """Edit an existing payment."""
    sale = get_object_or_404(Sale, id=sale_id)
    payment = get_object_or_404(Payment, id=payment_id, sale=sale)
    
    # Calculate balance excluding this payment
    total_paid = sale.payments.exclude(id=payment_id).aggregate(Sum('amount'))['amount__sum'] or 0
    balance = sale.total_amount - total_paid
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            edited_payment = form.save(commit=False)
            
            # Validate that payment amount doesn't exceed balance
            if edited_payment.amount > balance:
                form.add_error('amount', f'Payment amount exceeds remaining balance (GHS{balance}).')
            else:
                edited_payment.save()
                
                # Update sale payment status
                update_sale_payment_status(sale)
                
                messages.success(request, f'Payment updated successfully.')
                return redirect('payment_list', sale_id=sale.id)
    else:
        form = PaymentForm(instance=payment)
    
    context = {
        'form': form,
        'sale': sale,
        'payment': payment,
        'balance': balance + payment.amount,  # Add current payment amount to available balance
    }
    
    return render(request, 'juice_app/sale/sale_payment_edit.html', context)

@login_required
def payment_delete(request, sale_id, payment_id):
    """Delete a payment."""
    sale = get_object_or_404(Sale, id=sale_id)
    payment = get_object_or_404(Payment, id=payment_id, sale=sale)
    
    if request.method == 'POST':
        payment.delete()
        
        # Update sale payment status
        update_sale_payment_status(sale)
        
        messages.success(request, f'Payment deleted successfully.')
        return redirect('payment_list', sale_id=sale.id)
    
    context = {
        'sale': sale,
        'payment': payment,
    }
    
    return render(request, 'juice_app/sale/sale_payment_delete.html', context)

def update_sale_payment_status(sale):
    """Update the payment status of a sale based on payments."""
    total_paid = sale.payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    if total_paid >= sale.total_amount:
        sale.payment_status = 'paid'
    elif total_paid > 0:
        sale.payment_status = 'partial'
    else:
        sale.payment_status = 'pending'
    
    sale.save()



from juice_app.utils.pdf_generator import generate_sale_receipt_pdf

@login_required
def sale_receipt_pdf(request, sale_id):
    """Generate and serve a PDF receipt for a sale."""
    sale = get_object_or_404(Sale, id=sale_id)
    
    # Get all payments for this sale
    payments = sale.payments.all().order_by('-payment_date')
    
    # Generate the PDF
    pdf = generate_sale_receipt_pdf(sale, payments)
    
    # Create the HTTP response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"Receipt_{sale.invoice_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response