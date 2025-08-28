from django import template

# Reutilizamos el catálogo con emojis que ya tenés en el proyecto
try:
    from monedas.forms import CURRENCIES
except Exception:
    CURRENCIES = {}

register = template.Library()

@register.filter
def dict_get(d, key):
    """Acceso seguro a diccionarios en plantillas: {{ dict|dict_get:clave }}"""
    try:
        return d.get(key) if isinstance(d, dict) else None
    except Exception:
        return None

@register.filter
def flag(code):
    """
    Devuelve el emoji de bandera para un código ISO 4217 (USD, EUR, PYG, BRL, etc.).
    Uso: {{ "USD"|flag }}  -> 🇺🇸
    """
    if not code:
        return ""
    info = CURRENCIES.get(str(code).upper())
    return info.get("emoji") if isinstance(info, dict) else ""
