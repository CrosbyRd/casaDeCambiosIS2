"""
Módulo de modelos para la aplicación **Roles**.

Contiene la definición del modelo Role, que permite agrupar permisos
y asignarlos a usuarios del sistema.

Modelo incluido:
    - Role
"""
from django.db import models

# Create your models here.
# roles/models.py
from django.db import models
from django.contrib.auth.models import Permission

class Role(models.Model):
    """
    Representa un **rol de usuario** que agrupa permisos específicos.

    Un rol permite controlar el acceso a funcionalidades del sistema,
    simplificando la gestión de permisos para grupos de usuarios.

    :param str name: Nombre único del rol.
    :param str description: Descripción opcional del rol.
    :param permissions: Conjunto de permisos asignados al rol.
    :type permissions: ManyToManyField[Permission]
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Rol")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    permissions = models.ManyToManyField(
        Permission,
        verbose_name="Permisos",
        blank=True,
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

        managed = False
        default_permissions = ()
        permissions = [
            ("access_roles_panel", "Puede acceder al panel de Roles"),
            ("delete_roles", "Puede eliminar roles"),
        ]

    def __str__(self):
        return self.name