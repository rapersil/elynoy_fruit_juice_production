from django.db import models
from .validators import *
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extension of the Django User model to store additional user information.
    """
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    phone = models.CharField(max_length=20, validators=[validate_phone_number], blank=True)
    department = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Bottle(models.Model):
    """Model to represent bottle sizes used in product packaging."""
    size = models.CharField(max_length=20, validators=[validate_bottle_size], 
                           help_text="Bottle size (e.g., 350ml, 700ml)")
    description = models.TextField(blank=True, help_text="Additional details about the bottle")
    is_active = models.BooleanField(default=True, help_text="Whether this bottle size is in use")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='bottles',
        help_text="User who created this bottle size"
    )

    class Meta:
        ordering = ['size']
        verbose_name = 'Bottle Size'
        verbose_name_plural = 'Bottle Sizes'

    def __str__(self):
        return self.size
    



class Customer(models.Model):
    """Model to represent customers who can be suppliers, buyers, or both."""
    name = models.CharField(max_length=100, help_text="Name of the customer or company")
    contact_person = models.CharField(max_length=100, blank=True, help_text="Primary contact person")
    phone = models.CharField(max_length=20, validators=[validate_phone_number], 
                            help_text="Contact phone number")
    email = models.EmailField(validators=[validate_email], help_text="Contact email address")
    address = models.TextField(help_text="Physical address")
    is_supplier = models.BooleanField(default=False, help_text="Whether this customer supplies raw materials")
    is_buyer = models.BooleanField(default=True, help_text="Whether this customer buys finished products")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, 
                                      validators=[validate_non_negative], 
                                      help_text="Maximum credit extended to this customer (for buyers)")
    payment_terms = models.CharField(max_length=50, blank=True, 
                                   help_text="Payment terms (e.g., Net 30, COD)")
    notes = models.TextField(blank=True, help_text="Additional notes about this customer")
    is_active = models.BooleanField(default=True, help_text="Whether this customer is active")
    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        customer_type = []
        if self.is_supplier:
            customer_type.append('Supplier')
        if self.is_buyer:
            customer_type.append('Buyer')
        type_str = ' & '.join(customer_type)
        return f"{self.name} ({type_str})"
    



class RawMaterial(models.Model):
    """Model to represent raw materials used in production."""
    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('unit', 'Units'),
        ('liter', 'Liters'),
        ('gram', 'Grams'),
    ]
    
    name = models.CharField(max_length=100, help_text="Name of the raw material")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, help_text="Unit of measurement")
    quantity_in_stock = models.DecimalField(
        max_digits=10, decimal_places=2, 
        validators=[validate_non_negative],
        help_text="Current quantity in stock"
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[validate_positive],
        help_text="Cost per unit"
    )
    supplier = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        limit_choices_to={'is_supplier': True},
        help_text="Primary supplier of this material"
    )
    last_purchase_date = models.DateField(null=True, blank=True, help_text="Date of last purchase")
    reorder_level = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[validate_non_negative],
        help_text="Quantity at which to reorder"
    )
    is_fruit = models.BooleanField(default=False, help_text="Whether this is a fruit raw material")
    last_updated = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, help_text="Additional details about this material")
      # Add this field
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='raw_materials',
        help_text="User who created this raw material"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Raw Material'
        verbose_name_plural = 'Raw Materials'

    def __str__(self):
        return f"{self.name} ({self.unit})"
    
    @property
    def needs_reorder(self):
        """Return True if material quantity is at or below reorder level."""
        return self.quantity_in_stock <= self.reorder_level
    





class Product(models.Model):
    """Model to represent finished products."""
    name = models.CharField(max_length=100, help_text="Product name")
    sku = models.CharField(
        max_length=20, 
        unique=True, 
        validators=[validate_sku],
        help_text="Stock Keeping Unit (unique identifier)"
    )
    bottle = models.ForeignKey(
        Bottle, 
        on_delete=models.PROTECT, 
        help_text="Bottle size used for this product"
    )
    description = models.TextField(help_text="Product description")
    ingredients_description = models.TextField(help_text="Description of ingredients for labeling")
    production_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_non_negative],
        help_text="Cost to produce one unit (calculated from recipe)"
    )
    markup_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[validate_markup_percentage],
        default=50.00,
        help_text="Markup percentage for pricing (0-200%)"
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_non_negative],
        help_text="Selling price per unit"
    )
    stock_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_non_negative],
        default=0.00,
        help_text="Current quantity in stock"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this product is active/available"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.name} ({self.bottle.size})"

    def calculate_selling_price(self):
        """Calculate selling price based on production cost and markup."""
        return round(self.production_cost * (1 + (self.markup_percentage / 100)), 2)
    
    @classmethod
    def generate_sku(cls, bottle_size):
        """Generate a unique SKU for a new product."""
        # Create a prefix based on bottle size (e.g., convert "350ml" to "35")
        if bottle_size:
            # Extract numeric part from bottle size (e.g., "350ml" -> "350")
            size_digits = ''.join(filter(str.isdigit, bottle_size))
            # Take first 2 digits or pad if less
            if len(size_digits) >= 2:
                prefix = size_digits[:2]
            else:
                prefix = size_digits.zfill(2)
        else:
            prefix = "00"  # Default if no bottle size
            
        # Count existing products with this prefix to determine sequential number
        today = timezone.now().date()
        year_short = str(today.year)[-2:]  # Last 2 digits of year
        month = str(today.month).zfill(2)  # Month with leading zero
        
        # Format: JC-{prefix}-{year(2)}{month}-{sequential}
        base_sku = f"JC-{prefix}-{year_short}{month}"
        
        # Find the highest sequential number for this base SKU
        existing_skus = cls.objects.filter(sku__startswith=base_sku).values_list('sku', flat=True)
        highest_seq = 0
        
        for sku in existing_skus:
            try:
                # Extract sequential number from SKU (e.g., "JC-35-2305-001" -> "001")
                seq = int(sku.split('-')[-1])
                highest_seq = max(highest_seq, seq)
            except (ValueError, IndexError):
                continue
        
        # Create new SKU with incremented sequential number
        new_seq = highest_seq + 1
        return f"{base_sku}-{new_seq:03d}"  # e.g., JC-35-2305-001
    
    # def save(self, *args, **kwargs):
    #     """Override save to ensure selling price is updated."""
    #     if self.production_cost and self.markup_percentage:
    #         self.selling_price = self.calculate_selling_price()
    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        """Override save to ensure selling price is updated."""
        if self.production_cost is not None and self.markup_percentage is not None:
            self.selling_price = self.calculate_selling_price()
        elif not self.selling_price:  # If selling price is not already set
            self.selling_price = 0.00  # Default value
        super().save(*args, **kwargs)


class ProductionBatch(models.Model):
    """Model to represent a batch of products being produced."""
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        help_text="Product being produced"
    )
    batch_number = models.CharField(
        max_length=20, 
        unique=True, 
        validators=[validate_batch_number],
        help_text="Unique batch identifier (BATCH-YYYY-MM-DD-NNN)"
    )
    planned_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_positive],
        help_text="Planned production quantity"
    )
    actual_quantity_produced = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_non_negative],
        null=True, blank=True,
        help_text="Actual quantity produced (filled upon completion)"
    )
    production_date = models.DateField(
        help_text="Date production started"
    )
    completion_date = models.DateField(
        null=True, blank=True,
        help_text="Date production completed"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='planned',
        help_text="Current status of the batch"
    )
    produced_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='production_batches',
        help_text="User who managed this production batch"
    )
    quality_check_passed = models.BooleanField(
        null=True, blank=True,
        help_text="Whether quality check was passed (null if not checked yet)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this production batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Production Batch'
        verbose_name_plural = 'Production Batches'
        ordering = ['-production_date', 'batch_number']

    def __str__(self):
        return f"{self.batch_number} - {self.product.name} ({self.status})"

    @property
    def total_material_cost(self):
        """Calculate the total cost of materials used in this batch."""
        return sum(usage.actual_quantity_used * usage.raw_material.unit_cost 
                  for usage in self.material_usages.all())
    

class Recipe(models.Model):
    """
    Model representing the recipe/formula for a product, defining which raw 
    materials are required and in what quantities.
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='ingredients',
        help_text="Product this recipe ingredient is for"
    )
    raw_material = models.ForeignKey(
        RawMaterial, 
        on_delete=models.CASCADE,
        help_text="Raw material used in this recipe"
    )
    quantity_required = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[MinValueValidator(0.0001)],
        help_text="Quantity required per unit of product"
    )
    notes = models.TextField(
        blank=True,
        help_text="Special instructions or notes about this ingredient"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is a primary ingredient in the product"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Order in which ingredients are added in production"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Recipe Ingredient'
        verbose_name_plural = 'Recipe Ingredients'
        ordering = ['product', 'order', 'raw_material']
        unique_together = ['product', 'raw_material']
        indexes = [
            models.Index(fields=['product', 'raw_material']),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.raw_material.name} ({self.quantity_required} {self.raw_material.unit})"
    
    def clean(self):
        """Validate that quantity is appropriate for the material unit type."""
        super().clean()
        from django.core.exceptions import ValidationError
        
        # Ensure quantity is not excessive
        # if self.quantity_required > 1000000:
        #     raise ValidationError("Quantity required seems unreasonably high")
            
    def save(self, *args, **kwargs):
        """Override save to run clean and validate."""
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def ingredient_cost(self):
        """Calculate the cost of this ingredient in the recipe."""
        return self.quantity_required * self.raw_material.unit_cost
    
    def calculate_required_quantity(self, batch_quantity):
        """
        Calculate how much of this raw material is needed for a batch.
        
        Args:
            batch_quantity: Number of product units to produce
            
        Returns:
            Decimal: Total quantity required for the batch
        """
        return self.quantity_required * batch_quantity

class PurchaseOrder(models.Model):
    """Model to represent purchase orders for raw materials from suppliers."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('partial', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    po_number = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Purchase order number"
    )
    supplier = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT,
        limit_choices_to={'is_supplier': True},
        help_text="Supplier for this purchase order"
    )
    order_date = models.DateField(
        help_text="Date order was placed"
    )
    expected_delivery_date = models.DateField(
        null=True, blank=True,
        help_text="Expected date of delivery"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        help_text="Current status of the purchase order"
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[validate_non_negative],
        default=0.00,
        help_text="Total amount of the purchase order"
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending',
        help_text="Current payment status"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='purchase_orders',
        help_text="User who created this purchase order"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this purchase order"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-order_date', 'po_number']

    def __str__(self):
        return f"PO #{self.po_number} - {self.supplier.name} ({self.status})"
    
    def calculate_total(self):
        """Calculate the total amount of the purchase order from its items."""
        return sum(item.total_price for item in self.items.all())
    
    def save(self, *args, **kwargs):
        """Override save to ensure total is updated."""
        # Only update total if it has items (for existing POs)
        if not self.pk is None:
            self.total_amount = self.calculate_total()
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    """Model to represent items in a purchase order."""
    purchase_order = models.ForeignKey(
        PurchaseOrder, 
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Purchase order this item belongs to"
    )
    raw_material = models.ForeignKey(
        RawMaterial, 
        on_delete=models.PROTECT,
        help_text="Raw material being ordered"
    )
    quantity_ordered = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_positive],
        help_text="Quantity ordered"
    )
    quantity_received = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_non_negative],
        default=0.00,
        help_text="Quantity received so far"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_positive],
        help_text="Price per unit"
    )
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[validate_non_negative],
        help_text="Total price for this item (quantity * unit price)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.raw_material.name} - {self.quantity_ordered} {self.raw_material.unit}"
    
    def save(self, *args, **kwargs):
        """Override save to calculate total price."""
        self.total_price = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)
        # Update the purchase order total
        self.purchase_order.save()

    def update_inventory_on_receipt(self, quantity_receiving):
        """Update inventory when items are received."""
        if quantity_receiving > 0:
            # Update the received quantity
            self.quantity_received += quantity_receiving
            if self.quantity_received > self.quantity_ordered:
                self.quantity_received = self.quantity_ordered
                
            # Update the raw material inventory
            raw_material = self.raw_material
            raw_material.quantity_in_stock += quantity_receiving
            raw_material.last_purchase_date = self.purchase_order.order_date
            raw_material.save()
            
            # Save the updated item
            self.save()
            
            # Update purchase order status if needed
            po = self.purchase_order
            all_items = po.items.all()
            if all(item.quantity_received >= item.quantity_ordered for item in all_items):
                po.status = 'received'
            elif any(item.quantity_received > 0 for item in all_items):
                po.status = 'partial'
            po.save()



class Sale(models.Model):
    """Model to represent sales to customers."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Invoice number"
    )
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT,
        limit_choices_to={'is_buyer': True},
        help_text="Customer for this sale"
    )
    sale_date = models.DateField(
        help_text="Date of sale"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        help_text="Current status of the sale"
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[validate_non_negative],
        default=0.00,
        help_text="Total amount of the sale"
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending',
        help_text="Current payment status"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='sales',
        help_text="User who created this sale"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this sale"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-sale_date', 'invoice_number']

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name} ({self.status})"
    
    def calculate_total(self):
        """Calculate the total amount of the sale from its items."""
        return sum(item.total_price for item in self.items.all())
    
    def save(self, *args, **kwargs):
        """Override save to ensure total is updated."""
        # Only update total if it has items (for existing sales)
        if not self.pk is None:
            self.total_amount = self.calculate_total()
        super().save(*args, **kwargs)


class MaterialUsage(models.Model):
    """Model to track raw material usage in production batches."""
    batch = models.ForeignKey(
        ProductionBatch, 
        on_delete=models.CASCADE,
        related_name='material_usages',
        help_text="Production batch this usage is for"
    )
    raw_material = models.ForeignKey(
        RawMaterial, 
        on_delete=models.PROTECT,
        help_text="Raw material used"
    )
    planned_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[validate_positive],
        help_text="Planned quantity to use"
    )
    actual_quantity_used = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[validate_non_negative],
        null=True, blank=True,
        help_text="Actual quantity used (filled upon batch completion)"
    )
    waste_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[validate_non_negative],
        default=0,
        help_text="Quantity wasted during production"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this material usage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Material Usage'
        verbose_name_plural = 'Material Usages'
        unique_together = ['batch', 'raw_material']

    def __str__(self):
        return f"{self.batch.batch_number}: {self.raw_material.name} ({self.actual_quantity_used or self.planned_quantity} {self.raw_material.unit})"





class SaleItem(models.Model):
    """Model to represent items in a sale."""
    sale = models.ForeignKey(
        Sale, 
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Sale this item belongs to"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT,
        help_text="Product being sold"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_positive],
        help_text="Quantity sold"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[validate_positive],
        help_text="Price per unit"
    )
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[validate_non_negative],
        help_text="Total price for this item (quantity * unit price)"
    )
    batch_numbers = models.TextField(
        blank=True,
        help_text="Batch numbers this product came from (comma separated)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'

    def __str__(self):
        return f"{self.product.name} - {self.quantity} @ {self.unit_price}"
    
    def save(self, *args, **kwargs):
        """Override save to calculate total price."""
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Update the sale total
        self.sale.save()

