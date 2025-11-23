# configuracion/templatetags/configuracion_extras.py

from django import template
from decimal import Decimal
import locale

register = template.Library()

# Define la configuración regional para Paraguay (o la que uses)
# 'es_PY' o 'es_ES.UTF-8' o similar, dependiendo de tu sistema operativo.
# Para Linux/Mac, 'es_PY.UTF-8' o 'es_ES.UTF-8'.
# Para Windows, podría ser 'Spanish_Spain' o 'es_PY'.
# Si el locale falla, se usará un formato simple de Python.
try:
    locale.setlocale(locale.LC_ALL, 'es_PY.UTF-8')
except locale.Error:
    try:
        # Intenta otra variante común
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
    except locale.Error:
        # Fallback si no encuentra el locale
        pass


@register.filter
def formatear_moneda(value):
    """
    Formatea un número con separadores de miles y dos decimales,
    usando la configuración regional. Si no es un número, devuelve el valor.
    """
    if value is None or value == "":
        return value
    
    try:
        # Asegurarse de que es un Decimal o float
        number = Decimal(value)
        # Formato de moneda con separador de miles
        # %s es el símbolo de la moneda (vacío), %d son los decimales (2)
        # El 0 indica la posición del número en la tupla
        return locale.format_string("%d", number, grouping=True).replace(",", ".")
    except:
        # Si no se puede convertir, devuelve el valor original
        return value