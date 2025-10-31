from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
import string

def generate_otp_code(length=6):
    """Genera un código OTP alfanumérico."""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(user, subject, message_template, minutes_valid=5):
    """
    Genera un OTP, lo guarda en el usuario y lo envía por correo.
    Retorna True si el correo se envió con éxito, False en caso contrario.
    """
    user.verification_code = generate_otp_code()
    user.code_created_at = timezone.now()
    user.save(update_fields=['verification_code', 'code_created_at'])

    message = message_template.format(code=user.verification_code, minutes=minutes_valid)
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Aquí podrías loggear el error
        print(f"Error al enviar OTP a {user.email}: {e}")
        return False

def validate_otp_code(user, code, minutes_valid=5):
    """
    Valida si el código OTP proporcionado es correcto y no ha expirado.
    """
    if not user.verification_code or not user.code_created_at:
        return False

    is_valid_code = (user.verification_code == code)
    is_not_expired = (timezone.now() <= user.code_created_at + timedelta(minutes=minutes_valid))

    return is_valid_code and is_not_expired

from clientes.models import Cliente
from .models import CustomUser # Asumiendo que CustomUser está en .models

SESSION_KEY = 'cliente_activo_id'

def get_cliente_activo(request):
    cliente_id = request.session.get(SESSION_KEY)
    if cliente_id:
        try:
            return Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            pass
    return None
