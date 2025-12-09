from django import template

register = template.Library()

@register.filter(name='format_miles')
def format_miles(value):
    """
    Convierte un número a entero y le agrega separador de miles con punto.
    Ejemplo: 100354.75 -> 100.354
    """
    try:
        value = int(float(value))  # solo la parte entera
        return f"{value:,}".replace(",", ".")  # separador de miles con punto
    except (ValueError, TypeError):
        return value
