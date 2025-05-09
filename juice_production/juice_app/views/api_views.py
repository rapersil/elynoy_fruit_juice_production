from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..models import Product, Recipe

@login_required
def api_product_recipe(request, product_id):
    """API endpoint to get product recipe details."""
    try:
        product = Product.objects.get(id=product_id)
        recipe = Recipe.objects.filter(product=product).order_by('order')
        
        recipe_data = []
        for item in recipe:
            recipe_data.append({
                'id': item.id,
                'raw_material_id': item.raw_material.id,
                'raw_material_name': item.raw_material.name,
                'raw_material_unit': item.raw_material.unit,
                'quantity_required': float(item.quantity_required),
                'is_primary': item.is_primary,
                'order': item.order,
                'notes': item.notes,
            })
        
        return JsonResponse({
            'product_id': product.id,
            'product_name': product.name,
            'recipe': recipe_data,
            'success': True
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
@login_required
def api_product_details(request, product_id):
    """API endpoint to get product details including price."""
    try:
        product = Product.objects.get(id=product_id)
        
        return JsonResponse({
            'product_id': product.id,
            'product_name': product.name,
            'selling_price': float(product.selling_price),
            'stock_quantity': float(product.stock_quantity),
            'success': True
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)