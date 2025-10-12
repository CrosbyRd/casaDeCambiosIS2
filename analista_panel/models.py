
# =========================
# models.py
# =========================
from django.db import models


class AnalistaPanelPermissions(models.Model):
    """
    Modelo "contenedor" para registrar permisos del app sin crear tablas.
    - managed = False  → no migra/crea tabla
    - default_permissions = () → desactiva add/change/delete/view por defecto
    - Meta.permissions → declara permisos custom
    """

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            (
                "access_analista_dashboard",
                "Puede acceder al dashboard del Analista",
            ),
            # Permisos escalables para el rol Analista (por si luego segmentamos vistas):
            (
                "access_exchange_rates",
                "Puede acceder a Gestión de Tasas (ajuste manual + auditoría)",
            ),
            (
                "view_profits_module",
                "Puede ver el módulo de Ganancias (cuando esté disponible)",
            ),
        )
