from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from datetime import timedelta
from ..models import RawMaterial, Product, ProductionBatch, Sale, PurchaseOrder, SaleItem

@login_required
def inventory_report(request):
    """Generate inventory report."""
    # Raw Materials inventory
    raw_materials = RawMaterial.objects.all().order_by('name')
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
    """Generate production report."""
    # Get date range from request or default to last 30 days
    end_date = timezone.now().date()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=30)).isoformat())
    end_date_param = request.GET.get('end_date', end_date.isoformat())
    
    try:
        start_date = timezone.datetime.fromisoformat(start_date).date()
        end_date = timezone.datetime.fromisoformat(end_date_param).date()
    except (ValueError, TypeError):
        start_date = end_date - timedelta(days=30)
    
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
    
    # Production by month
    production_by_month = batches.filter(
        status='completed'
    ).annotate(
        month=TruncMonth('production_date')
    ).values('month').annotate(
        total_quantity=Sum('actual_quantity_produced'),
        batch_count=Count('id')
    ).order_by('month')
    
    # Production efficiency (actual vs planned)
    production_efficiency = batches.filter(
        status='completed', 
        actual_quantity_produced__isnull=False
    ).aggregate(
        total_planned=Sum('planned_quantity'),
        total_actual=Sum('actual_quantity_produced')
    )
    
    efficiency_percentage = 0
    if production_efficiency['total_planned'] and production_efficiency['total_actual']:
        efficiency_percentage = (production_efficiency['total_actual'] / production_efficiency['total_planned']) * 100
    
    context = {
        'batches': batches,
        'production_by_product': production_by_product,
        'production_by_month': production_by_month,
        'start_date': start_date,
        'end_date': end_date,
        'efficiency_percentage': efficiency_percentage,
        'production_efficiency': production_efficiency,
    }
    
    return render(request, 'juice_app/reports/report_production.html', context)

@login_required
def sales_report(request):
    """Generate sales report."""
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
    
    # Total sales amount
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Sales by product
    sales_by_product = SaleItem.objects.filter(
        sale__sale_date__range=[start_date, end_date],
        sale__status__in=['confirmed', 'shipped', 'delivered']
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')
    
    # Sales by week
    sales_by_week = sales.annotate(
        week=TruncWeek('sale_date')
    ).values('week').annotate(
        total_sales=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('week')
    
    # Top customers
    top_customers = sales.values('customer__name', 'customer_id', 'customer__id').annotate(
    total_spend=Sum('total_amount'),
    order_count=Count('id')
    ).order_by('-total_spend')[:5]
    
    context = {
        'sales': sales,
        'total_sales': total_sales,
        'sales_by_product': sales_by_product,
        'sales_by_week': sales_by_week,
        'top_customers': top_customers,
        'start_date': start_date,
        'end_date': end_date,
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