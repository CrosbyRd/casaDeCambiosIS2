from datetime import timedelta
from decimal import Decimal
from django.apps import apps
from django.utils import timezone

def get_cotizacion_vigente(moneda_obj):
    """
    Intenta leer la última cotización de la app 'cotizaciones' y valida 15 minutos.
    Se asume un modelo 'Cotizacion' con campos: moneda(FK Moneda), compra, venta, created_at.
    Si tu esquema difiere, devolvemos None y la UI mostrará un aviso.
    """
    Cotizacion = apps.get_model("cotizaciones", "Cotizacion")
    if Cotizacion is None:
        return None

    # adaptado al caso habitual: última por created_at
    try:
        c = (Cotizacion.objects
             .filter(moneda=moneda_obj)
             .order_by("-created_at")
             .first())
        if not c:
            return None

        created = getattr(c, "created_at", None)
        compra = Decimal(getattr(c, "compra"))
        venta  = Decimal(getattr(c, "venta"))
        if created is None:
            return None

        vigente = (timezone.now() - created) <= timedelta(minutes=15)
        return {
            "compra": compra,
            "venta":  venta,
            "created_at": created,
            "vigente": vigente,
        }
    except Exception:
        return None
