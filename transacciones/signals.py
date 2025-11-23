from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaccion
from facturacion_electronica.tasks import generar_factura_electronica_task

@receiver(post_save, sender=Transaccion)
def disparar_facturacion_electronica(sender, instance, created, **kwargs):
    """
    Dispara la tarea de facturación electrónica cuando una transacción
    alcanza el estado 'procesando_acreditacion'.
    """
    if instance.estado == 'procesando_acreditacion':
        # Verificar si ya se ha disparado una factura para esta transacción
        # para evitar duplicados en caso de múltiples guardados.
        # Esta lógica asume que no se debería generar más de una factura.
        if not instance.documentos_electronicos.exists():
            generar_factura_electronica_task.delay(
                emisor_id=None,  # El emisor se obtiene dentro de la tarea
                transaccion_id=str(instance.id),
                email_receptor=instance.usuario_operador.email
            )
