# notificaciones/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from cotizaciones.signals import cotizacion_actualizada
from .models import PreferenciasNotificacion, Notificacion
from .tasks import notificar_cambio_de_tasa_a_usuarios

@receiver(cotizacion_actualizada)
def crear_notificacion_por_cambio_tasa(sender, instance, venta_cambio=False, compra_cambio=False, **kwargs):
    """
    Escucha la señal de cambio de cotización y crea notificaciones para los usuarios interesados.
    """
    # --- ¡AQUÍ ESTÁ LA CLAVE! ---
    # Si no hubo cambio ni en la venta ni en la compra, no hacemos nada.
    if not venta_cambio and not compra_cambio:
        return
    User = get_user_model()  # Se obtiene el modelo de usuario.
    
    # Construir el mensaje usando las propiedades que incluyen comisión
    mensaje = f"¡Atención! La cotización de {instance.moneda_destino.nombre} ({instance.moneda_destino.codigo}) ha cambiado. "
    if venta_cambio:
        mensaje += f"Nuevo precio de venta: {instance.total_venta:,.0f} Gs. "
    if compra_cambio:
        mensaje += f"Nuevo precio de compra: {instance.total_compra:,.0f} Gs."

    # Llama a la tarea de Celery para que se ejecute en segundo plano
    notificar_cambio_de_tasa_a_usuarios.delay(instance.id, mensaje, compra_cambio, venta_cambio)



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_preferencias_para_nuevo_usuario(sender, instance, created, **kwargs):
    """
    Crea un perfil de preferencias de notificación automáticamente para cada nuevo usuario.
    """
    if created:
        PreferenciasNotificacion.objects.create(usuario=instance)
