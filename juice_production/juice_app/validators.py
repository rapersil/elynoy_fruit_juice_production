from django.core.exceptions import ValidationError
import re

def validate_non_negative(value):
    """Validate that a value is not negative."""
    if value < 0:
        raise ValidationError('Value cannot be negative.')

def validate_positive(value):
    """Validate that a value is positive."""
    if value <= 0:
        raise ValidationError('Value must be positive.')

def validate_phone_number(value):
    """Validate phone number format."""
    pattern = r'^\+?1?\d{9,15}$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid phone number format. Use +1XXXXXXXXXX or similar format.')

def validate_email(value):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid email format.')

def validate_markup_percentage(value):
    """Validate markup percentage is within reasonable range."""
    if value < 0 or value > 200:
        raise ValidationError('Markup percentage must be between 0 and 200.')

def validate_batch_number(value):
    """Validate batch number format."""
    pattern = r'^BATCH-\d{4}-\d{2}-\d{2}-\d{3}$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid batch number format. Must be BATCH-YYYY-MM-DD-NNN.')

def validate_sku(value):
    """Validate SKU format."""
    pattern = r'^[A-Z]{2,4}-\d{3,6}$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid SKU format. Must be XX-NNNN or similar.')

def validate_bottle_size(value):
    """Validate bottle size format."""
    pattern = r'^\d+ml$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid bottle size format. Must be like 350ml, 500ml, etc.')

def validate_sufficient_stock(raw_material, quantity_needed):
    """Validate there is sufficient stock for production."""
    if raw_material.quantity_in_stock < quantity_needed:
        raise ValidationError(
            f'Insufficient stock for {raw_material.name}. ' 
            f'Available: {raw_material.quantity_in_stock} {raw_material.unit}, ' 
            f'Needed: {quantity_needed} {raw_material.unit}'
        )