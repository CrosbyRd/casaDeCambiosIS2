# medios_acreditacion/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class TipoMedioAcreditacion(models.Model):
    class Nombre(models.TextChoices):
        CUENTA_SIPAP = "CUENTA_SIPAP", "Cuenta bancaria (SIPAP)"
        BILLETERA    = "BILLETERA",    "Billetera electrónica"

    nombre = models.CharField(
        max_length=40,
        choices=Nombre.choices,
        help_text="Selecciona el tipo de medio de acreditación permitido en el sistema."
    )

    # Si querés replicar la forma de pagos 1:1, mantenemos estos campos (opcionales)
    comision_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Comisión en % del monto total (0–100)."
    )
    bonificacion_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Descuento/bonificación en % aplicado (0–100)."
    )

    activo = models.BooleanField(default=True, help_text="Si está desactivado, no se podrá usar en operaciones.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Medio de Acreditación"
        verbose_name_plural = "Tipos de Medio de Acreditación"
        ordering = ["nombre"]
        unique_together = [("nombre",)]  # evita duplicados del mismo tipo

    def __str__(self) -> str:
        return self.get_nombre_display()
