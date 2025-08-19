from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Definimos los tipos de usuario
    class UserTypes(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        CAJERO = 'CAJERO', 'Cajero'
        CLIENTE = 'CLIENTE', 'Cliente'

    # Campo para diferenciar el tipo de usuario
    tipo_usuario = models.CharField(
        max_length=50,
        choices=UserTypes.choices,
        default=UserTypes.CLIENTE
    )

    # Puedes agregar más campos si lo necesitas, por ejemplo:
    # telefono = models.CharField(max_length=20, blank=True, null=True)
    # direccion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.username