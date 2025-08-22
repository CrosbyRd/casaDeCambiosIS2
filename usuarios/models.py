# proyecto/usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from clientes.models import Cliente 
from roles.models import Role


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
        default=UserTypes.CLIENTE     #si no se especifica el tipo de usuario es por default CLIENTE
    )

    clientes = models.ManyToManyField(
        Cliente,
        blank=True,
        related_name='usuarios'  # Permite acceder desde Cliente a sus usuarios
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Rol del usuario'
    )

    def __str__(self):
        return self.username
    

