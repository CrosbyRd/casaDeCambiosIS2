# operaciones/models.py

from django.db import models

class CanalFinanciero(models.Model):
    """
    Representa una entidad financiera (Banco, Billetera) con la que
    la Casa de Cambio opera para mover Guaraníes.
    Es una configuración interna y administrativa.
    """
    TIPO_CANAL_CHOICES = [
        ('banco', 'Cuenta Bancaria'),
        ('billetera', 'Billetera Electrónica'),
    ]

    nombre = models.CharField(max_length=100, unique=True, help_text="Ej: Banco Itaú, Tigo Money")
    tipo = models.CharField(max_length=20, choices=TIPO_CANAL_CHOICES)
    activo = models.BooleanField(default=True, help_text="Indica si este canal está operativo para transacciones.")

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "Canal Financiero"
        verbose_name_plural = "Canales Financieros"


class Tauser(models.Model):
    """
    Representa una Terminal de Autoservicio (Tauser) física.
    """
    codigo_identificador = models.CharField(max_length=20, unique=True, help_text="ID único de la terminal. Ej: TAUSER-001")
    ubicacion = models.CharField(max_length=255, help_text="Dirección o descripción de la ubicación de la terminal.")
    activo = models.BooleanField(default=True, help_text="Indica si la terminal está operativa.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.codigo_identificador

    class Meta:
        verbose_name = "Terminal de Autoservicio (Tauser)"
        verbose_name_plural = "Terminales de Autoservicio (Tauser)"
