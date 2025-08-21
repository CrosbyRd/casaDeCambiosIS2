<<<<<<< HEAD
# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from roles.models import Role 
=======
# proyecto/usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
>>>>>>> development

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    roles = models.ManyToManyField(
        Role,
        verbose_name="Roles",
        blank=True,
        related_name="users"
    )
<<<<<<< HEAD

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
=======
    
    # Relacionamos el usuario con el rol (uno a uno)
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
>>>>>>> development
