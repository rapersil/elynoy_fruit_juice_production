from django.shortcuts import render
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.db.models.functions import TruncMonth, TruncQuarter, TruncYear
from datetime import datetime, timedelta
from ..models import Product, RawMaterial, ProductionBatch, Sale, Customer

def dashboard_view(request):
    """Dashboard view showing high-level metrics and recent activity."""
    # Current date for calculations
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Count key metrics
    products_count = Product.objects.filter(is_active=True).count()
    batches_in_progress = ProductionBatch.objects.filter(status='in_progress').count()
    total_sales = Sale.objects.filter(
        sale_date__gte=month_start,
        status__in=['confirmed', 'shipped', 'delivered']
    ).count()
    
    # Get low stock materials
    low_stock_items = RawMaterial.objects.filter(
        quantity_in_stock__lte=F('reorder_level')
    ).order_by('quantity_in_stock')[:5]
    low_stock_materials = low_stock_items.count()
    
    # Recent production batches
    recent_production = ProductionBatch.objects.all().order_by('-production_date')[:5]
    
    # Recent sales
    recent_sales = Sale.objects.all().order_by('-sale_date')[:5]
    
    # Monthly Production Data
    # Get data for the past 12 months
    twelve_months_ago = today - timedelta(days=365)
    
    # Get all batches from the past 12 months
    all_batches = ProductionBatch.objects.filter(
        production_date__gte=twelve_months_ago
    )
    
    # Prepare monthly data
    monthly_production = [0] * 12
    monthly_planned = [0] * 12
    
    # Group by month and aggregate
    monthly_data = all_batches.annotate(
        month=TruncMonth('production_date')
    ).values('month').annotate(
        planned=Sum('planned_quantity'),
        actual=Sum('actual_quantity_produced', filter=Q(status='completed'))
    ).order_by('month')
    
    # Map monthly data to arrays
    current_month = today.month
    current_year = today.year
    
    for data in monthly_data:
        month = data['month'].month
        year = data['month'].year
        
        # Calculate position in the array (relative to the current month)
        if year == current_year:
            index = month - 1  # 0-indexed
        else:
            # Previous year
            index = month - 1 + (12 - current_month)
            if index >= 12:  # Ensure it wraps properly
                index = index - 12
        
        if 0 <= index < 12:
            monthly_planned[index] = float(data['planned'] or 0)
            monthly_production[index] = float(data['actual'] or 0)
    
    # Quarterly Production Data
    quarterly_production = [0] * 4
    quarterly_planned = [0] * 4
    
    # Group by quarter and aggregate
    quarterly_data = all_batches.annotate(
        quarter=TruncQuarter('production_date')
    ).values('quarter').annotate(
        planned=Sum('planned_quantity'),
        actual=Sum('actual_quantity_produced', filter=Q(status='completed'))
    ).order_by('quarter')
    
    # Current quarter (1-4)
    current_quarter = (today.month - 1) // 3 + 1
    
    for data in quarterly_data:
        quarter_date = data['quarter']
        quarter = (quarter_date.month - 1) // 3 + 1  # 1-indexed
        quarter_year = quarter_date.year
        
        # Calculate position in the array
        if quarter_year == current_year:
            index = quarter - 1  # 0-indexed
        else:
            # Previous year
            index = quarter - 1 + (4 - current_quarter)
            if index >= 4:  # Ensure it wraps properly
                index = index - 4
        
        if 0 <= index < 4:
            quarterly_planned[index] = float(data['planned'] or 0)
            quarterly_production[index] = float(data['actual'] or 0)
    
    # Yearly Production Data
    # Get data for the past 5 years
    five_years_ago = today.replace(year=today.year - 5)
    
    yearly_data = all_batches.filter(
        production_date__gte=five_years_ago
    ).annotate(
        year=TruncYear('production_date')
    ).values('year').annotate(
        planned=Sum('planned_quantity'),
        actual=Sum('actual_quantity_produced', filter=Q(status='completed'))
    ).order_by('year')
    
    # Prepare yearly data arrays
    year_labels = []
    yearly_planned = []
    yearly_production = []
    
    for data in yearly_data:
        year_labels.append(str(data['year'].year))
        yearly_planned.append(float(data['planned'] or 0))
        yearly_production.append(float(data['actual'] or 0))
    
    context = {
        'products_count': products_count,
        'batches_in_progress': batches_in_progress,
        'total_sales': total_sales,
        'low_stock_materials': low_stock_materials,
        'low_stock_items': low_stock_items,
        'recent_production': recent_production,
        'recent_sales': recent_sales,
        'monthly_production': monthly_production,
        'monthly_planned': monthly_planned,
        'quarterly_production': quarterly_production,
        'quarterly_planned': quarterly_planned,
        'yearly_production': yearly_production,
        'yearly_planned': yearly_planned,
        'year_labels': year_labels,
    }
    
    return render(request, 'juice_app/dashboard/dashboard.html', context)