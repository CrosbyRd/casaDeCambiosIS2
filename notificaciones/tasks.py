# /home/richar-carballo/Escritorio/IS2/casaDeCambiosIS2/notificaciones/tasks.py (NUEVO ARCHIVO)
from celery import shared_task
from django.contrib.auth import get_user_model
from .emails import enviar_email_cambio_tasa
from .models import Notificacion
from cotizaciones.models import Cotizacion

@shared_task
def notificar_cambio_de_tasa_a_usuarios(cotizacion_id, mensaje):
    """
    Tarea de Celery para enviar notificaciones de cambio de tasa en segundo plano.
    """
    try:
        cotizacion = Cotizacion.objects.get(pk=cotizacion_id)
    except Cotizacion.DoesNotExist:
        # Si la cotización fue eliminada, no hacemos nada.
        return

    User = get_user_model()
    usuarios_a_notificar = User.objects.filter(is_active=True)

    for usuario in usuarios_a_notificar:
        # 1. Crear la notificación en el panel (esto es rápido)
        Notificacion.objects.create(
            destinatario=usuario,
            mensaje=mensaje,
        )

        # 2. Comprobar preferencias y enviar email (esto es lo que queremos en segundo plano)
        quiere_recibir_email = True
        preferencias = getattr(usuario, 'preferencias_notificacion', None)
        if preferencias:
            quiere_recibir_email = preferencias.recibir_email_tasa_cambio

        if quiere_recibir_email:
            enviar_email_cambio_tasa(usuario, mensaje, cotizacion)

    return f"Notificaciones enviadas para la cotización {cotizacion_id} a {usuarios_a_notificar.count()} usuarios."
