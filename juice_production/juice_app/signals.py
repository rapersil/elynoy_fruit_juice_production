
from .models import *  # Import all models
from .models import Recipe  # Explicitly import Recipe
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=MaterialUsage)
def update_raw_material_stock(sender, instance, **kwargs):
    """
    Update raw material stock when material usage is recorded upon batch completion.
    Only deduct from stock when actual_quantity_used is set (batch is completed).
    """
    # Check if this is an update (not a new record) and actual_quantity_used is set
    if instance.actual_quantity_used is not None and instance.batch.status == 'completed':
        raw_material = instance.raw_material
        # Deduct the actual used quantity from stock
        raw_material.quantity_in_stock -= instance.actual_quantity_used
        # Ensure stock doesn't go negative
        if raw_material.quantity_in_stock < 0:
            raw_material.quantity_in_stock = 0
        raw_material.save()

@receiver(post_save, sender=ProductionBatch)
def update_product_stock(sender, instance, created, **kwargs):
    """
    Update product stock when a production batch is completed.
    Add the actual produced quantity to product stock.
    """
    if not created and instance.status == 'completed' and instance.actual_quantity_produced:
        product = instance.product
        product.stock_quantity += instance.actual_quantity_produced
        product.save()


@receiver(post_save, sender=Sale)
def update_product_stock_on_sale_confirmation(sender, instance, **kwargs):
    """Update product stock when a sale is confirmed."""
    if instance.status == 'confirmed':
        for item in instance.items.all():
            product = item.product
            # Deduct sold quantity from stock
            product.stock_quantity -= item.quantity
            # Ensure stock doesn't go negative
            if product.stock_quantity < 0:
                product.stock_quantity = 0
            product.save()



@receiver(post_save, sender=RawMaterial)
def update_product_prices_on_material_cost_change(sender, instance, **kwargs):
    """
    Update product prices when raw material costs change.
    Find all recipes using this raw material and update the related products.
    """
    # Find all recipes that use this raw material
    recipes = Recipe.objects.filter(raw_material=instance)
    
    # Get unique products from these recipes
    products = set(recipe.product for recipe in recipes)
    
    # Update each product's production cost and selling price
    for product in products:
        # Calculate total cost from all ingredients
        total_cost = 0
        for ingredient in product.ingredients.all():
            total_cost += ingredient.quantity_required * ingredient.raw_material.unit_cost
        
        # Update product cost and trigger selling price calculation
        product.production_cost = total_cost
        product.save()



@receiver(post_save, sender=Recipe)
def update_product_cost_on_recipe_change(sender, instance, **kwargs):
    """Update product cost when a recipe ingredient is added or changed."""
    product = instance.product
    # Calculate total cost of all ingredients
    total_cost = sum(ingredient.ingredient_cost for ingredient in product.ingredients.all())
    
    # Update product cost and selling price
    product.production_cost = total_cost
    product.save()  # This will trigger calculation of selling_price in Product.save method

@receiver(post_delete, sender=Recipe)
def update_product_cost_on_recipe_delete(sender, instance, **kwargs):
    """Update product cost when a recipe ingredient is deleted."""
    product = instance.product
    # Calculate total cost of all remaining ingredients
    total_cost = sum(ingredient.ingredient_cost for ingredient in product.ingredients.all())
    
    # Update product cost and selling price
    product.production_cost = total_cost
    product.save()  # This will trigger calculation of selling_price