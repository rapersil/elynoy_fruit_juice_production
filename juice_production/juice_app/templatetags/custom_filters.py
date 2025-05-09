from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiplies the value by the argument.
    
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0



@register.filter(name='abs')
def absolute_value(value):
    """
    Returns the absolute value of a number.
    
    Usage: {{ value|abs }}
    Example: {{ -10.5|abs }} will output 10.5
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0
    


@register.filter(name='divide')
def divide(value, arg):
    """
    Divides the value by the argument.
    
    Usage: {{ value|divide:arg }}
    Example: {{ 10|divide:2 }} will output 5
    
    If division by zero is attempted, returns 0.
    """
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0
    

@register.filter(name='split')
def split_string(value, arg):
    """
    Splits a string by the specified delimiter.
    
    Usage: {{ value|split:arg }}
    Example: {{ "a,b,c"|split:"," }} will output ['a', 'b', 'c']
    """
    return value.split(arg)

@register.filter(name='subtract')
def subtract(value, arg):
    """
    Subtracts the argument from the value.
    
    Usage: {{ value|subtract:arg }}
    Example: {{ 10|subtract:5 }} will output 5
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='split')
def split(value, arg):
    """
    Splits a string based on the provided delimiter.
    
    Usage: {{ value|split:"," }}
    """
    return value.split(arg)


# @register.filter(name='multiply')
# def multiply_values(value, arg):
#     """Multiply the value by the argument."""
#     try:
#         return float(value) * float(arg)
#     except (ValueError, TypeError):
#         return 0

# @register.filter(name='divide')
# def divide_values(value, arg):
#     """Divide the value by the argument."""
#     try:
#         arg = float(arg)
#         if arg == 0:
#             return 0
#         return float(value) / arg
#     except (ValueError, TypeError):
#         return 0