from django import template

register = template.Library()

@register.filter
def currency(value):
    """
    Formatea un número como moneda en PYG: separador de miles "." y decimales ","
    Ejemplo: 1234567.89 -> 1.234.567,89
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value
    entero = int(value)
    decimales = round(abs(value - entero) * 100)
    entero_formateado = f"{entero:,}".replace(",", ".")
    return f"{entero_formateado},{decimales:02d}"
