from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from juice_app.views.dashboard_views import *
from juice_app.views.auth_views import *
from juice_app.views.raw_material_views import *
from juice_app.views.bottle_views import *
from juice_app.views.product_views import *
from juice_app.views.production_views import *
from juice_app.views.customer_views import *                
from juice_app.views.supplier_views import *
from juice_app.views.purchase_order_views import *            
from juice_app.views.sale_views import *
from juice_app.views.report_views import *
from juice_app.views.user_views import *
from juice_app.views.api_views import *



urlpatterns = [
    path('logout/', logout_view, name='logout'),
    # Dashboard
    path('', dashboard_view, name='dashboard'),
    
    # Raw Materials
    path('raw-materials/', raw_material_list, name='raw_material_list'),
    path('raw-materials/<int:material_id>/', raw_material_detail, name='raw_material_detail'),
    path('raw-materials/new/', raw_material_new, name='raw_material_new'),
    path('raw-materials/<int:material_id>/edit/', raw_material_edit, name='raw_material_edit'),
    path('raw-materials/<int:material_id>/delete/', raw_material_delete, name='raw_material_delete'),
    
    # Bottles
    path('bottles/', bottle_list, name='bottle_list'),
    path('bottles/<int:bottle_id>/', bottle_detail, name='bottle_detail'),
    path('bottles/new/', bottle_new, name='bottle_new'),
    path('bottles/<int:bottle_id>/edit/', bottle_edit, name='bottle_edit'),
    path('bottles/<int:bottle_id>/delete/', bottle_delete, name='bottle_delete'),

    
    # # Products
    path('products/', product_list, name='product_list'),
    path('products/<int:product_id>/', product_detail, name='product_detail'),
    path('products/new/', product_new, name='product_new'),
    path('products/<int:product_id>/edit/', product_edit, name='product_edit'),
    
    # Production
    path('production/', production_list, name='production_list'),
    path('production/<int:batch_id>/', production_detail, name='production_detail'),
    path('production/new/', production_new, name='production_new'),
    path('production/<int:batch_id>/start/', production_start, name='production_start'),
    path('production/<int:batch_id>/complete/', production_complete, name='production_complete'),
    path('production/<int:batch_id>/cancel/', production_cancel, name='production_cancel'),
    path('production/<int:batch_id>/edit/', production_edit, name='production_edit'),
    
    # Customers
    path('customers/', customer_list, name='customer_list'),
    path('customers/<int:customer_id>/', customer_detail, name='customer_detail'),
    path('customers/new/', customer_new, name='customer_new'),
    path('customers/<int:customer_id>/edit/', customer_edit, name='customer_edit'),
    
    # Suppliers (specific view for customers who are suppliers)
    path('suppliers/', supplier_list, name='supplier_list'),
    
    # # Purchase Orders
    path('purchases/', purchase_order_list, name='purchase_order_list'),
    path('purchases/<int:po_id>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchases/new/', purchase_order_new, name='purchase_order_new'),
    path('purchases/<int:po_id>/edit/', purchase_order_edit, name='purchase_order_edit'),
    path('purchases/<int:po_id>/receive/', purchase_order_receive, name='purchase_order_receive'),
    
    # # Sales
    path('sales/', sale_list, name='sale_list'),
    path('sales/<int:sale_id>/', sale_detail, name='sale_detail'),
    path('sales/new/', sale_new, name='sale_new'),
    path('sales/<int:sale_id>/edit/', sale_edit, name='sale_edit'),
    path('sales/<int:sale_id>/confirm/', sale_confirm, name='sale_confirm'),
    path('sales/<int:sale_id>/receipt/', sale_receipt, name='sale_receipt'),
    path('sales/dashboard/', sales_dashboard, name='sales_dashboard'),
    path('sales/top-customers/', top_customers_analysis, name='top_customers_analysis'),
    # Payments
    path('sales/<int:sale_id>/payments/', payment_list, name='payment_list'),
    path('sales/<int:sale_id>/payments/add/', payment_add, name='payment_add'),
    path('sales/<int:sale_id>/payments/', payment_list, name='payment_list'),
    path('sales/<int:sale_id>/payments/add/', payment_add, name='payment_add'),
    path('sales/<int:sale_id>/payments/<int:payment_id>/', payment_detail, name='payment_detail'),
    path('sales/<int:sale_id>/payments/<int:payment_id>/edit/', payment_edit, name='payment_edit'),
    path('sales/<int:sale_id>/payments/<int:payment_id>/delete/', payment_delete, name='payment_delete'),
    path('sales/<int:sale_id>/receipt/pdf/', sale_receipt_pdf, name='sale_receipt_pdf'),
    path('reports/sales/pdf/', sales_report_pdf, name='sales_report_pdf'),
    
    # # Users
    path('profile/', user_profile, name='user_profile'),
    path('user/profile/edit/',edit_profile_view,name="edit_profile"),
    
    # # Reports
    path('reports/inventory/', inventory_report, name='inventory_report'),
    path('reports/production/', production_report, name='production_report'),
    path('reports/sales/', sales_report, name='sales_report'),
    path('reports/sales/excel/', sales_report_excel, name='sales_report_excel'),
    
    # # API endpoints for AJAX calls
    path('api/product/<int:product_id>/recipe/', api_product_recipe, name='api_product_recipe'),
    path('api/product/<int:product_id>/details/', api_product_details, name='api_product_details'),


    # Add to the urlpatterns in urls.py
    path('accounts/password/change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('accounts/password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('accounts/password/reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/password/admin-reset/<int:user_id>/', admin_reset_user_password, name='admin_reset_password'),
    path('accounts/register//', register_view, name='register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)