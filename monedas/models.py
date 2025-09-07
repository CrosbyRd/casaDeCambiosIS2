from django.db import models

class Moneda(models.Model):
    codigo = models.CharField(max_length=5, unique=True)  # USD, EUR, PYG
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=5)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Requerimientos ERS
    decimales = models.PositiveSmallIntegerField(default=2)  
    minima_denominacion = models.PositiveIntegerField(default=1)
    ultima_actualizacion_tasa = models.DateTimeField(null=True, blank=True)

    admite_en_linea = models.BooleanField(default=True)
    admite_terminal = models.BooleanField(default=True)


    class Meta:
        permissions = [
            ("access_monedas_section", "Puede acceder a la sección de Monedas"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
