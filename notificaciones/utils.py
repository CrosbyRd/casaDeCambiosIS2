#util.py
from django.core.mail import send_mail
from django.conf import settings
from .models import Notificacion

def crear_notificacion(usuario, titulo, mensaje, tipo="INFO", enviar_correo=True):
    """
    Crea una notificación para el usuario y opcionalmente envía un correo.
    """
    notificacion = Notificacion.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo
    )

    if enviar_correo and usuario.email:
        send_mail(
            subject=f"[Global Exchange] {titulo}",
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            fail_silently=True,
        )

    return notificacion
