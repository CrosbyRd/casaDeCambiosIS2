# notificaciones/signals.py (NUEVO ARCHIVO)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from cotizaciones.signals import cotizacion_actualizada
from .models import PreferenciasNotificacion, Notificacion
from .tasks import notificar_cambio_de_tasa_a_usuarios

@receiver(cotizacion_actualizada)
def crear_notificacion_por_cambio_tasa(sender, instance, venta_cambio, compra_cambio, **kwargs):
    """
    Escucha la señal de cambio de cotización y crea notificaciones para los usuarios interesados.
    """
    User = get_user_model() # Se obtiene el modelo de usuario.
    # Construir el mensaje
    mensaje = f"¡Atención! La cotización de {instance.moneda_destino.nombre} ({instance.moneda_destino.codigo}) ha cambiado. "
    if venta_cambio:
        mensaje += f"Nuevo precio de venta: {instance.valor_venta:,.2f} Gs. "
    if compra_cambio:
        mensaje += f"Nuevo precio de compra: {instance.valor_compra:,.2f} Gs."

    # Llama a la tarea de Celery para que se ejecute en segundo plano.
    # .delay() es la forma de ejecutarla asíncronamente.
    # Pasamos IDs en lugar de objetos completos, es una buena práctica.
    notificar_cambio_de_tasa_a_usuarios.delay(instance.id, mensaje)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_preferencias_para_nuevo_usuario(sender, instance, created, **kwargs):
    """
    Crea un perfil de preferencias de notificación automáticamente para cada nuevo usuario.
    """
    if created:
        PreferenciasNotificacion.objects.create(usuario=instance)
