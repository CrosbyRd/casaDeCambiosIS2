from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
import random
from django.utils import timezone

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    tipo_usuario = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Administrador'),
            ('ANALISTA', 'Analista'),
            ('CLIENTE', 'Cliente')
        ],
        default='CLIENTE'
    )

    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    code_created_at = models.DateTimeField(blank=True, null=True)

    def generate_verification_code(self):
        self.verification_code = f"{random.randint(100000, 999999)}"
        self.code_created_at = timezone.now()  # <- siempre aware
        self.save()

    def is_code_valid(self, code, minutes_valid=5):
        """Devuelve True si el código coincide y no expiró"""
        if not self.verification_code or not self.code_created_at:
            return False
        if str(self.verification_code).strip() != str(code).strip():
            return False
        now = timezone.now()
        # Aseguramos que code_created_at sea timezone-aware
        code_time = self.code_created_at
        if timezone.is_naive(code_time):
            code_time = timezone.make_aware(code_time, timezone.get_current_timezone())
        return now <= code_time + timedelta(minutes=minutes_valid)

    def __str__(self):
        return self.email