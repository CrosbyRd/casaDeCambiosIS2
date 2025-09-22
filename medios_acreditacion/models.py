from django.db import models

class CategoriaMedio(models.Model):
    codigo = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Código interno (ej: transferencia, billetera, pickup)"
    )
    requiere_datos_extra = models.BooleanField(
        default=True,
        help_text="Si el cliente debe cargar datos adicionales (número de cuenta, alias, etc.)"
    )
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medio de Acreditación"
        verbose_name_plural = "Medios de Acreditación"
        ordering = ["-ultima_modificacion"]

    def __str__(self):
        # Se muestra el código tal cual como nombre
        return self.codigo.capitalize()
