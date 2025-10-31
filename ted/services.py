# ted/services.py

"""
Servicios relacionados con cotizaciones y gestión de divisas del Tauser.

Este módulo define funciones utilitarias para consultar cotizaciones vigentes
de monedas y determinar si una cotización puede ser usada para operaciones de
compra o venta en el sistema. Incluye lógica de vigencia basada en tiempo y
configuraciones del sistema.

Constantes:
    BASE_CODIGO (str): Código de la moneda base del sistema (PYG).

Funciones:
    get_cotizacion_vigente(moneda_obj): Devuelve la cotización más reciente para
        una moneda destino, indicando si está vigente y si puede ser usada.
"""

from datetime import timedelta
from decimal import Decimal
from django.apps import apps
from django.utils import timezone
from django.conf import settings

BASE_CODIGO = "PYG"  # moneda base del sistema

def get_cotizacion_vigente(moneda_obj):
    """
    Obtiene la cotización más reciente para una moneda destino respecto a la moneda base.

    La función devuelve un diccionario con los valores de compra y venta, la fecha de
    actualización y flags de vigencia y uso, considerando la configuración de vigencia
    definida en `settings.TED_COTIZACION_VIGENCIA_MINUTES` y la opción de permitir
    cotizaciones expiradas con `TED_ALLOW_STALE_RATES`.

    :param moneda_obj: Instancia del modelo Moneda para la cual se desea la cotización.
    :type moneda_obj: monedas.models.Moneda

    :returns: Diccionario con la cotización y estados, o None si no hay cotización.
    :rtype: dict | None

    Diccionario retornado:
        - 'compra' (Decimal): Valor de compra de la moneda destino.
        - 'venta' (Decimal): Valor de venta de la moneda destino.
        - 'created_at' (datetime): Fecha y hora de la última actualización.
        - 'vigente' (bool): True si la cotización está dentro del tiempo de vigencia configurado.
        - 'usable' (bool): True si la cotización puede ser usada (vigente o permitido usar caducada).

    :notes:
        - La vigencia por defecto es de 15 minutos si `TED_COTIZACION_VIGENCIA_MINUTES` no está definido.
        - La función retorna None si no se encuentra la moneda, el modelo o la cotización.
        - Utiliza `apps.get_model` para obtener el modelo `Cotizacion` de manera dinámica.
    """
    if not moneda_obj:
        return None

    Cotizacion = apps.get_model("cotizaciones", "Cotizacion")
    if Cotizacion is None:
        return None

    c = (
        Cotizacion.objects
        .filter(moneda_base__codigo__iexact=BASE_CODIGO, moneda_destino=moneda_obj)
        .order_by("-fecha_actualizacion")
        .first()
    )
    if not c:
        return None

    # Estas propiedades deben existir en tu modelo (ya las usaste con éxito):
    compra = Decimal(c.total_compra)
    venta  = Decimal(c.total_venta)
    created = getattr(c, "fecha_actualizacion", None)
    if not created:
        return None

    minutes = getattr(settings, "TED_COTIZACION_VIGENCIA_MINUTES", 15)
    vigente = (timezone.now() - created) <= timedelta(minutes=minutes)

    allow_stale = getattr(settings, "TED_ALLOW_STALE_RATES", False)
    usable = vigente or allow_stale

    return {
        "compra": compra,
        "venta": venta,
        "created_at": created,
        "vigente": vigente,
        "usable": usable,
    }
