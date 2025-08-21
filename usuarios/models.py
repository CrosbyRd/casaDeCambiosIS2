# proyecto/usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import uuid

class CustomUser(AbstractUser):
    class UserTypes(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        CAJERO = 'CAJERO', 'Cajero'
        CLIENTE = 'CLIENTE', 'Cliente'

    tipo_usuario = models.CharField(
        max_length=50,
        choices=UserTypes.choices,
        default=UserTypes.CLIENTE
    )

    rol = models.OneToOneField(
        'Rol',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Rol asignado a este usuario"
    )

    def __str__(self):
        return self.username

class Permiso(models.Model):
    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre descriptivo del permiso (ej. 'Crear Cliente')")
    codigo = models.CharField(max_length=50, unique=True, help_text="Código único para usar en el código (ej. 'crear_cliente')")
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nombre

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    permisos = models.ManyToManyField(Permiso, related_name='roles')

    def __str__(self):
        return self.nombre

# --- MFA por email: códigos de login ---
class EmailLoginCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="email_login_codes")
    code = models.CharField(max_length=6)  # 6 dígitos
    mfa_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)  # referencia opaca para el cliente
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["mfa_token"]),
            models.Index(fields=["user", "used"]),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])

    def __str__(self):
        masked = "******"
        return f"EmailLoginCode(user={self.user}, code={masked}, used={self.used})"

    @classmethod
    def create_for_user(cls, user, lifetime_minutes: int = 10, code: str | None = None):
        if code is None:
            import random
            code = f"{random.randint(0, 999999):06d}"
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=lifetime_minutes),
        )
