from django.db import models

class Moneda(models.Model):
    codigo = models.CharField(max_length=5, unique=True)  # USD, EUR, PYG
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=5)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
