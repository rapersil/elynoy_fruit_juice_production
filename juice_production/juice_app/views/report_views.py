import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField, Avg
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import timedelta
from ..models import Payment, RawMaterial, Product, ProductionBatch, Sale, PurchaseOrder, SaleItem

@login_required
def inventory_report(request):
    """Generate inventory report."""
    # Raw Materials inventory
    raw_materials = RawMaterial.objects.all().order_by('quantity_in_stock')
    low_stock_materials = raw_materials.filter(quantity_in_stock__lte=F('reorder_level'))
    
    # Products inventory
    products = Product.objects.filter(is_active=True).order_by('name')
    low_stock_products = products.filter(stock_quantity__lt=10)  # Arbitrary threshold
    
    # Top 5 materials by value
    top_materials_by_value = raw_materials.annotate(
        total_value=ExpressionWrapper(
            F('quantity_in_stock') * F('unit_cost'),
            output_field=DecimalField()
        )
    ).order_by('-total_value')[:5]
    
    # Top 5 products by value
    top_products_by_value = products.annotate(
        total_value=ExpressionWrapper(
            F('stock_quantity') * F('selling_price'),
            output_field=DecimalField()
        )
    ).order_by('-total_value')[:5]
    
    context = {
        'raw_materials': raw_materials,
        'products': products,
        'low_stock_materials': low_stock_materials,
        'low_stock_products': low_stock_products,
        'top_materials_by_value': top_materials_by_value,
        'top_products_by_value': top_products_by_value,
        'report_date': timezone.now().date(),
    }
    
    return render(request, 'juice_app/reports/report_inventory.html', context)

@login_required
def production_report(request):
    """Generate comprehensive production inventory report."""
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=30)).isoformat())
    end_date_param = request.GET.get('end_date', end_date.isoformat())
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date_param).date()
    except (ValueError, TypeError):
        start_date = end_date - timedelta(days=30)
    
    # Get filter parameters
    inventory_type = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'all')
    sort_by = request.GET.get('sort', 'value')
    
    # Raw Materials inventory data
    raw_materials = RawMaterial.objects.all()
    raw_materials_count = raw_materials.count()
    raw_materials_value = sum(material.quantity_in_stock * material.unit_cost for material in raw_materials)
    
    # Low stock materials
    low_stock_materials = raw_materials.filter(quantity_in_stock__lte=F('reorder_level'))
    
    # Finished Products inventory data
    products = Product.objects.filter(is_active=True)
    products_count = products.count()
    products_value = sum(product.stock_quantity * product.selling_price for product in products)
    
    # Active production batches (in progress)
    active_batches = ProductionBatch.objects.filter(status='in_progress')
    active_batches_count = active_batches.count()
    
    # Calculate in-production value
    in_production_value = 0
    for batch in active_batches:
        # Sum the cost of materials allocated to this batch
        material_cost = batch.material_usages.aggregate(
            total=Sum(F('planned_quantity') * F('raw_material__unit_cost'))
        )['total'] or 0
        in_production_value += material_cost
    
    # Total inventory value
    total_inventory_value = raw_materials_value + products_value + in_production_value
    
    # Production batches in date range
    batches = ProductionBatch.objects.filter(
        production_date__range=[start_date, end_date]
    ).order_by('-production_date')
    
    # Production by product
    production_by_product = batches.filter(
        status='completed'
    ).values('product__name').annotate(
        total_quantity=Sum('actual_quantity_produced'),
        batch_count=Count('id')
    ).order_by('-total_quantity')
    
    # Inventory turnover calculation (simplified)
    # Get sales in the period
    total_product_sales = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(
        total_cost=Sum(F('quantity') * F('product__production_cost'))
    )['total_cost'] or 0
    
    # Calculate average inventory value over the period
    # This should ideally use historical data points, but we'll simplify
    avg_inventory_value = total_inventory_value / 2  # very simplified
    
    # Calculate inventory turnover rate
    inventory_turnover_rate = total_product_sales / avg_inventory_value if avg_inventory_value > 0 else 0
    
    # Days inventory outstanding
    days_inventory_outstanding = 365 / inventory_turnover_rate if inventory_turnover_rate > 0 else 0
    
    # Inventory efficiency percentage
    ideal_turnover = 12  # An ideal of monthly turnover (industry dependent)
    inventory_efficiency = (inventory_turnover_rate / ideal_turnover) * 100 if ideal_turnover > 0 else 0
    
    # Calculate production efficiency
    production_efficiency_data = batches.filter(
        status='completed', 
        actual_quantity_produced__isnull=False
    ).aggregate(
        total_planned=Sum('planned_quantity'),
        total_actual=Sum('actual_quantity_produced')
    )
    
    efficiency_percentage = 0
    if production_efficiency_data['total_planned'] and production_efficiency_data['total_actual']:
        efficiency_percentage = (production_efficiency_data['total_actual'] / production_efficiency_data['total_planned']) * 100
    
    # Top items by value
    # Combine raw materials, products, and in-production batches for a unified top items list
    top_value_items = []
    
    # Add raw materials
    for material in raw_materials:
        value = material.quantity_in_stock * material.unit_cost
        if value > 0:
            top_value_items.append({
                'id': material.id,
                'name': material.name,
                'type': 'raw_material',
                'total_value': value
            })
    
    # Add products
    for product in products:
        value = product.stock_quantity * product.selling_price
        if value > 0:
            top_value_items.append({
                'id': product.id,
                'name': product.name,
                'type': 'product',
                'total_value': value
            })
    
    # Add in-production batches
    for batch in active_batches:
        material_cost = batch.material_usages.aggregate(
            total=Sum(F('planned_quantity') * F('raw_material__unit_cost'))
        )['total'] or 0
        
        if material_cost > 0:
            top_value_items.append({
                'id': batch.id,
                'name': f"{batch.batch_number} ({batch.product.name})",
                'type': 'in_production',
                'total_value': material_cost
            })
    
    # Sort and limit to top 10
    top_value_items = sorted(top_value_items, key=lambda x: x['total_value'], reverse=True)[:10]
    
    # Top products by production volume
    top_produced_products = []
    for product_data in production_by_product[:5]:  # Top 5
        product_name = product_data['product__name']
        product_batches = batches.filter(
            status='completed', 
            product__name=product_name
        )
        
        # Calculate efficiency for this product
        product_efficiency_data = product_batches.aggregate(
            planned=Sum('planned_quantity'),
            actual=Sum('actual_quantity_produced')
        )
        
        product_efficiency = 0
        if product_efficiency_data['planned'] and product_efficiency_data['actual']:
            product_efficiency = (product_efficiency_data['actual'] / product_efficiency_data['planned']) * 100
        
        # Calculate production value
        production_value = product_efficiency_data['actual'] * Product.objects.get(name=product_name).production_cost if product_efficiency_data['actual'] else 0
        
        top_produced_products.append({
            'name': product_name,
            'quantity_produced': product_data['total_quantity'],
            'efficiency': product_efficiency,
            'production_value': production_value
        })
    
   
    
    # Compile all low stock items
    low_stock_items = []
    
    # Add low stock raw materials
    for material in low_stock_materials:
        low_stock_items.append({
            'id': material.id,
            'name': material.name,
            'type': 'raw_material',
            'stock_quantity': material.quantity_in_stock,
            'reorder_level': material.reorder_level
        })
    
    # Add low stock products (using arbitrary threshold for demonstration)
    low_stock_products = products.filter(stock_quantity__lt=10)
    for product in low_stock_products:
        low_stock_items.append({
            'id': product.id,
            'name': product.name,
            'type': 'product',
            'stock_quantity': product.stock_quantity,
            'reorder_level': 5  # Arbitrary threshold
        })
    
    # Sort by criticality (how far below reorder level)
    for item in low_stock_items:
        item['criticality'] = item['reorder_level'] - item['stock_quantity']
    
    low_stock_items = sorted(low_stock_items, key=lambda x: x['criticality'], reverse=True)[:10]
    
    # Total production value
    total_production_value = sum(product['production_value'] for product in top_produced_products)
    
    context = {
        'raw_materials': raw_materials,
        'products': products,
        'production_batches': active_batches,
        'raw_materials_count': raw_materials_count,
        'raw_materials_value': raw_materials_value,
        'products_count': products_count,
        'products_value': products_value,
        'active_batches_count': active_batches_count,
        'in_production_value': in_production_value,
        'total_inventory_value': total_inventory_value,
        'low_stock_items': low_stock_items,
        'top_value_items': top_value_items,
        'inventory_turnover_rate': inventory_turnover_rate,
        'days_inventory_outstanding': days_inventory_outstanding,
        'inventory_efficiency': inventory_efficiency,
        'efficiency_percentage': efficiency_percentage,
        'production_efficiency': efficiency_percentage,
        'top_produced_products': top_produced_products,
        'total_production_value': total_production_value,
        'report_date': timezone.now().date(),
        'start_date': start_date,
        'end_date': end_date,
        'inventory_type': inventory_type,
        'status_filter': status_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'juice_app/reports/report_production.html', context)

@login_required
@login_required
def sales_report(request):
    """Generate comprehensive sales report with enhanced analytics."""
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=30)).isoformat())
    end_date_param = request.GET.get('end_date', end_date.isoformat())
    view_type = request.GET.get('view', 'daily')  # New parameter for viewing data (daily/weekly/monthly)
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date_param).date()
    except (ValueError, TypeError):
        start_date = end_date - timedelta(days=30)
    
    # Calculate previous period for comparison
    period_length = (end_date - start_date).days
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=period_length)
    
    # Sales in current date range
    sales = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    ).order_by('-sale_date')
    
    # Sales in previous period (for comparison)
    prev_sales = Sale.objects.filter(
        sale_date__range=[prev_start_date, prev_end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    )
    
    # Total sales metrics
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    prev_total_sales = prev_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Calculate growth percentage
    sales_trend = 0
    if prev_total_sales > 0:
        sales_trend = ((total_sales - prev_total_sales) / prev_total_sales) * 100
    
    # Sale counts and average values
    sale_count = sales.count()
    avg_order_value = total_sales / sale_count if sale_count > 0 else 0
    
    # Payment rate calculation
    paid_sales = sales.filter(payment_status='paid').count()
    payment_rate = (paid_sales / sale_count) * 100 if sale_count > 0 else 0
    
    # Products sold
    total_units = SaleItem.objects.filter(
        sale__in=sales
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Sales status breakdown
    confirmed_revenue = sales.filter(status='confirmed').aggregate(total=Sum('total_amount'))['total'] or 0
    shipped_revenue = sales.filter(status='shipped').aggregate(total=Sum('total_amount'))['total'] or 0
    delivered_revenue = sales.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
    cancelled_revenue = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status='cancelled'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Sales by payment method (new)
    payment_methods = Payment.objects.filter(
        sale__in=sales
    ).values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')

    print(payment_methods)
    
    # Top products
    top_products = SaleItem.objects.filter(
        sale__in=sales
    ).values('product__name', 'product__id').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price'),
        avg_price=Avg('unit_price')
    ).order_by('-revenue')[:10]
    
    # For chart data
    top_product_names = [p['product__name'] for p in top_products]
    top_product_values = [float(p['revenue']) for p in top_products]
    
    # Top customers
    top_customers = sales.values('customer__name', 'customer__id').annotate(
        total_spend=Sum('total_amount'),
        order_count=Count('id'),
        avg_order=Avg('total_amount')
    ).order_by('-total_spend')[:10]
    
    # Sales by time period for trend chart
    date_trunc = None
    if view_type == 'daily':
        date_trunc = TruncDay('sale_date')
    elif view_type == 'weekly':
        date_trunc = TruncWeek('sale_date')
    else:  # monthly
        date_trunc = TruncMonth('sale_date')
    
    sales_by_period = sales.annotate(
        period=date_trunc
    ).values('period').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('period')
    
    # Prepare data for charts
    trend_dates = []
    revenue_data = []
    order_counts = []
    
    for period_data in sales_by_period:
        if view_type == 'daily':
            trend_dates.append(period_data['period'].strftime('%d %b'))
        elif view_type == 'weekly':
            trend_dates.append(f"Week of {period_data['period'].strftime('%d %b')}")
        else:
            trend_dates.append(period_data['period'].strftime('%b %Y'))
            
        revenue_data.append(float(period_data['total']))
        order_counts.append(period_data['count'])
    
    # New: Product profitability analysis
    product_profitability = SaleItem.objects.filter(
        sale__in=sales
    ).values('product__name', 'product__production_cost').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price'),
        avg_selling_price=Avg('unit_price')
    ).order_by('-revenue')[:5]
    
    for item in product_profitability:
        if item['product__production_cost']:
            production_cost = item['product__production_cost']
            item['profit_margin'] = ((item['avg_selling_price'] - production_cost) / item['avg_selling_price']) * 100
        else:
            item['profit_margin'] = 0
    
    # New: Customer retention analysis
    repeat_customers = sales.values('customer').annotate(
        purchase_count=Count('id')
    ).filter(purchase_count__gt=1).count()
    
    repeat_customer_rate = (repeat_customers / sales.values('customer').distinct().count()) * 100 if sales.exists() else 0
    
    context = {
        'sales': sales[:20],  # Limit to 20 most recent for display
        'total_sales': total_sales,
        'sales_trend': sales_trend,
        'sale_count': sale_count,
        'avg_order_value': avg_order_value,
        'payment_rate': payment_rate,
        'total_units': total_units,
        'trend_dates': json.dumps(trend_dates),
        'revenue_data': json.dumps(revenue_data),
        'order_counts': json.dumps(order_counts),
        'top_customers': top_customers,
        'top_products': top_products,
        'top_product_names': json.dumps(top_product_names),
        'top_product_values': json.dumps(top_product_values),
        'confirmed_revenue': confirmed_revenue,
        'shipped_revenue': shipped_revenue,
        'delivered_revenue': delivered_revenue,
        'cancelled_revenue': cancelled_revenue,
        'payment_methods': payment_methods,
        'product_profitability': product_profitability,
        'repeat_customer_rate': repeat_customer_rate,
        'start_date': start_date,
        'end_date': end_date,
        'view_type': view_type,
    }
    
    return render(request, 'juice_app/reports/report_sales.html', context)



from django.http import HttpResponse
from ..utils.pdf_generator import generate_sales_report_pdf

@login_required
def sales_report_pdf(request):
    """Generate and serve a PDF sales report."""
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=30)).isoformat())
    end_date_param = request.GET.get('end_date', end_date.isoformat())
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date_param).date()
    except (ValueError, TypeError):
        start_date = end_date - timedelta(days=30)
    
    # Sales in date range
    sales = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    ).order_by('-sale_date')
    
    # Calculate summary data
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_count = sales.count()
    avg_sale = total_sales / total_count if total_count > 0 else 0
    
    # Total products sold
    total_products_sold = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Sales by status
    sales_by_status = list(sales.values('status').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('status'))
    
    # Top selling products
    top_products = list(SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).values('product__name').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price'),
        avg_price=Avg('unit_price')
    ).order_by('-revenue')[:10])
    
    # Prepare summary data
    summary_data = {
        'total_sales': total_sales,
        'total_count': total_count,
        'avg_sale': avg_sale,
        'total_products_sold': total_products_sold,
        'sales_by_status': sales_by_status,
        'top_products': top_products
    }
    
    # Generate the PDF
    pdf = generate_sales_report_pdf(start_date, end_date, sales, summary_data)
    
    # Create the HTTP response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"Sales_Report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response




from django.http import HttpResponse
from ..utils.excel_generator import generate_sales_report_excel

@login_required
def sales_report_excel(request):
    """Generate and serve an Excel sales report."""
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=30)).isoformat())
    end_date_param = request.GET.get('end_date', end_date.isoformat())
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date_param).date()
    except (ValueError, TypeError):
        start_date = end_date - timedelta(days=30)
    
    # Sales in date range
    sales = Sale.objects.filter(
        sale_date__range=[start_date, end_date],
        status__in=['confirmed', 'shipped', 'delivered']
    ).order_by('-sale_date')
    
    # Calculate summary data (same as in the PDF function)
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_count = sales.count()
    avg_sale = total_sales / total_count if total_count > 0 else 0
    
    # Total products sold
    total_products_sold = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # Sales by status
    sales_by_status = list(sales.values('status').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('status'))
    
    # Top selling products
    top_products = list(SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).values('product__name').annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price'),
        avg_price=Avg('unit_price')
    ).order_by('-revenue')[:10])
    
    # Prepare summary data
    summary_data = {
        'total_sales': total_sales,
        'total_count': total_count,
        'avg_sale': avg_sale,
        'total_products_sold': total_products_sold,
        'sales_by_status': sales_by_status,
        'top_products': top_products
    }
    
    # Generate the Excel file
    excel_file = generate_sales_report_excel(start_date, end_date, sales, summary_data)
    
    # Create the HTTP response
    response = HttpResponse(excel_file, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"Sales_Report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response