# cotizaciones/signals.py
from django.dispatch import Signal, receiver
from django.db.models.signals import post_save
from django.utils import timezone
from .models import Cotizacion, CotizacionHistorica

# Señal propia ya usada en tu modelo
cotizacion_actualizada = Signal()

@receiver(cotizacion_actualizada, dispatch_uid="cotiz_hist_por_cambio")
def registrar_historico_por_cambio(sender, instance: Cotizacion, venta_cambio: bool, compra_cambio: bool, **kwargs):
    # Registra snapshot cuando cambian valores/comisiones
    CotizacionHistorica.objects.create(
        moneda_base=instance.moneda_base,
        moneda_destino=instance.moneda_destino,
        valor_compra=instance.valor_compra,
        comision_compra=instance.comision_compra,
        valor_venta=instance.valor_venta,
        comision_venta=instance.comision_venta,
        fecha=timezone.now(),
        fuente="manual/api",
    )

@receiver(post_save, sender=Cotizacion, dispatch_uid="cotiz_hist_en_creacion")
def registrar_historico_en_creacion(sender, instance: Cotizacion, created: bool, **kwargs):
    # En la creación inicial tu save() no dispara la señal custom → garantizamos primer snapshot
    if created:
        CotizacionHistorica.objects.create(
            moneda_base=instance.moneda_base,
            moneda_destino=instance.moneda_destino,
            valor_compra=instance.valor_compra,
            comision_compra=instance.comision_compra,
            valor_venta=instance.valor_venta,
            comision_venta=instance.comision_venta,
            fecha=timezone.now(),
            fuente="inicial",
        )
