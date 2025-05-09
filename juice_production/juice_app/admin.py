from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from juice_app.models import (
    Bottle, RawMaterial, Customer, UserProfile, Product, 
    Recipe, ProductionBatch, MaterialUsage,
    PurchaseOrder, PurchaseOrderItem, Sale, SaleItem
)

# Inline admin classes
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

class RecipeInline(admin.TabularInline):
    model = Recipe
    extra = 1

class MaterialUsageInline(admin.TabularInline):
    model = MaterialUsage
    extra = 1

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

# Admin classes
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

class BottleAdmin(admin.ModelAdmin):
    list_display = ('size', 'description', 'is_active')
    search_fields = ('size', 'description')
    list_filter = ('is_active',)

class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'quantity_in_stock', 'unit_cost', 'supplier', 'reorder_level', 'needs_reorder')
    search_fields = ('name', 'supplier__name')
    list_filter = ('unit', 'is_fruit', 'supplier')

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'is_supplier', 'is_buyer', 'is_active')
    search_fields = ('name', 'contact_person', 'email')
    list_filter = ('is_supplier', 'is_buyer', 'is_active')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'bottle', 'production_cost', 'markup_percentage', 'selling_price', 'stock_quantity', 'is_active')
    search_fields = ('name', 'sku', 'description')
    list_filter = ('bottle', 'is_active')
    inlines = [RecipeInline]

class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'product', 'planned_quantity', 'actual_quantity_produced', 'production_date', 'status')
    search_fields = ('batch_number', 'product__name')
    list_filter = ('status', 'production_date', 'product')
    inlines = [MaterialUsageInline]

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'total_amount', 'status', 'payment_status')
    search_fields = ('po_number', 'supplier__name')
    list_filter = ('status', 'payment_status', 'order_date')
    inlines = [PurchaseOrderItemInline]

class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sale_date', 'total_amount', 'status', 'payment_status')
    search_fields = ('invoice_number', 'customer__name')
    list_filter = ('status', 'payment_status', 'sale_date')
    inlines = [SaleItemInline]

# Register models with admin site
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Bottle, BottleAdmin)
admin.site.register(RawMaterial, RawMaterialAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductionBatch, ProductionBatchAdmin)
admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(Sale, SaleAdmin)