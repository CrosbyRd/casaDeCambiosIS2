# ted/services.py
from datetime import timedelta
from decimal import Decimal
from django.apps import apps
from django.utils import timezone
from django.conf import settings

BASE_CODIGO = "PYG"  # moneda base del sistema

def get_cotizacion_vigente(moneda_obj):
    """
    Devuelve:
      {
        'compra': Decimal, 'venta': Decimal,
        'created_at': datetime, 'vigente': bool,
        'usable': bool,  # True si vigente o si TED_ALLOW_STALE_RATES está activo
      }
    La vigencia se controla con settings.TED_COTIZACION_VIGENCIA_MINUTES (default 15).
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
