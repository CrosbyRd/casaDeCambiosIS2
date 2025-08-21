# proyecto/usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # Definimos los tipos de usuario
    class UserTypes(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        ANALISTA = 'ANALISTA', 'Analista'
        CLIENTE = 'CLIENTE', 'Cliente'

    # Campo para diferenciar el tipo de usuario
    tipo_usuario = models.CharField(
        max_length=50,
        choices=UserTypes.choices,
        default=UserTypes.CLIENTE
    )

    def __str__(self):
        return self.username
    

