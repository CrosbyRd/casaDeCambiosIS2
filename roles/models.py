from django.db import models

# Create your models here.
# roles/models.py
from django.db import models
from django.contrib.auth.models import Permission

class Role(models.Model):
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