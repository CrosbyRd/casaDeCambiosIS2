"""
Modelos de la app TED.
======================

.. module:: ted.models
   :synopsis: Modelos propios del módulo TED.

Incluye:
- :class:`TedPerms`: contenedor mínimo de permisos.
- :class:`TedTerminal`: terminal físico (serial y ubicación) para persistir
  la dirección mostrada en el inventario y permitir expansión futura a múltiples
  terminales.
"""
from django.db import models


class TedPerms(models.Model):
    """
    Modelo mínimo para declarar permisos de la app TED.
    No se usa en lógica; solo existe para registrar el permiso custom.
    """
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("puede_operar_terminal", "Puede operar el terminal TED"),
            ("puede_gestionar_inventario", "Puede gestionar inventario TED"),
        ]


class TedTerminal(models.Model):
    """
    Representa una terminal física TED.

    :param serial: identificador único del equipo (ej. ``TED-AGSL-0001``).
    :param direccion: texto libre con la ubicación del equipo.
    :param created_at: fecha de creación.
    :param updated_at: última actualización.

    Este modelo permite persistir la ubicación que se muestra en el
    inventario y preparar el sistema para múltiples terminales en el futuro.
    """
    serial = models.CharField("Serial", max_length=50, unique=True)
    direccion = models.CharField("Ubicación", max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Terminal TED"
        verbose_name_plural = "Terminales TED"

    def __str__(self) -> str:
        return self.serial
