#util.py
"""
Módulo utilitario para la gestión de notificaciones del sistema.

Contiene funciones auxiliares para crear notificaciones y enviar correos electrónicos
a los usuarios de la plataforma Global Exchange.


"""
from django.core.mail import send_mail
from django.conf import settings
from .models import Notificacion

def crear_notificacion(usuario, titulo, mensaje, tipo="INFO", enviar_correo=True):
    """
    Crea una **notificación** para un usuario y, opcionalmente, envía un correo electrónico.

    Esta función permite registrar un evento informativo en el sistema de notificaciones
    y enviar un mensaje de correo si el usuario tiene configurado un correo electrónico válido.

    :param usuario: Usuario destinatario de la notificación.
    :type usuario: django.contrib.auth.models.User
    :param titulo: Título o encabezado breve de la notificación.
    :type titulo: str
    :param mensaje: Contenido principal del mensaje.
    :type mensaje: str
    :param tipo: Tipo o categoría de la notificación (por defecto: ``"INFO"``).
    :type tipo: str
    :param enviar_correo: Si es ``True``, envía un correo al usuario además de crear la notificación.
    :type enviar_correo: bool

    :returns: Instancia de la notificación creada.
    :rtype: notificaciones.models.Notificacion

    :raises django.core.mail.BadHeaderError: Si ocurre un error en el encabezado del correo.
    :raises Exception: Si ocurre un error inesperado al crear la notificación.

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
