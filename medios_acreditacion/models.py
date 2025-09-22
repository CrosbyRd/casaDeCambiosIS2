from django.db import models

class CategoriaMedio(models.Model):
    CODIGO_CHOICES = [
        ("transferencia", "Transferencia Bancaria"),
        ("billetera", "Billetera Electrónica"),
        ("pickup", "Retiro en Ventanilla (Pickup)"),
    ]

    codigo = models.CharField(
        max_length=50,
        choices=CODIGO_CHOICES,  # 🔹 lista fija
        unique=True,
        help_text="Seleccione el tipo de medio (ej: transferencia, billetera, pickup)"
    )
    # Moneda fija, NO editable
    moneda_predeterminada = models.CharField(
        max_length=10,
        default="PYG",
        editable=False,  # <- no aparece en forms
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
        return self.get_codigo_display()
