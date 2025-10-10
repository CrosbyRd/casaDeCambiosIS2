# notificaciones/emails.py (NUEVO ARCHIVO)

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

def enviar_email_cambio_tasa(usuario, mensaje_notificacion, cotizacion):
    """
    Envía un correo electrónico de notificación de cambio de tasa a un usuario.
    """
    subject = f"Actualización de Tasa de Cambio: {cotizacion.moneda_destino.codigo}"
    
    context = {
        'usuario': usuario,
        'mensaje_notificacion': mensaje_notificacion,
        'cotizacion': cotizacion,
        'nombre_sitio': 'Tu Casa de Cambio', # Puedes obtenerlo de settings si lo tienes configurado
    }
    
    # Renderizar el cuerpo del correo desde la plantilla HTML
    html_message = render_to_string('notificaciones/emails/cambio_tasa.html', context)
    
    # Crear una versión de texto plano para clientes de correo que no soportan HTML
    plain_message = strip_tags(html_message)
    
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [usuario.email]

    try:
        send_mail(
            subject,
            plain_message,
            from_email,
            to_email,
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Correo de notificación enviado exitosamente a {usuario.email}")
    except Exception as e:
        # Es buena idea registrar el error en un log
        print(f"Error al enviar correo de notificación a {usuario.email}: {e}")

