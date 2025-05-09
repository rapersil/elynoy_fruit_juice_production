from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import F
from ..models import (
    RawMaterial, Product, ProductionBatch, 
    Sale, PurchaseOrder
)

@login_required
def dashboard_view(request):
    """Dashboard view showing summary of key metrics."""
    context = {
        'raw_materials_count': RawMaterial.objects.count(),
        'products_count': Product.objects.count(),
        'low_stock_materials': RawMaterial.objects.filter(
            quantity_in_stock__lte=F('reorder_level')).count(),
        'recent_production': ProductionBatch.objects.order_by('-production_date')[:5],
        'recent_sales': Sale.objects.order_by('-sale_date')[:5],
        'pending_purchases': PurchaseOrder.objects.filter(
            status__in=['draft', 'submitted']).count(),
    }
    return render(request, 'juice_app/dashboard/dashboard.html', context)