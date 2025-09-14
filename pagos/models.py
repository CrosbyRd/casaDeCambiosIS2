from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class TipoMedioPago(models.Model):
    """
    Tipos de medios de pago: Tarjeta de crédito, Billetera electrónica, Cheque, etc.
    """
    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Ej.: 'Tarjeta de Crédito', 'Billetera Electrónica', 'Cheque'"
    )

    # Comisión aplicada sobre el monto de la operación (en %)
    comision_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Comisión en % del monto total de la transacción (0–100)."
    )

    # NUEVO: Bonificación/Descuento (en %)
    bonificacion_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Descuento en % aplicado (0–100)."
    )

    # Estado del medio de pago
    activo = models.BooleanField(
        default=True,
        help_text="Si está desactivado no se podrá utilizar en operaciones."
    )

    # Trazabilidad
    created_at = models.DateTimeField(auto_now_add=True)  # fecha de creación
    updated_at = models.DateTimeField(auto_now=True)      # última actualización

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de Medio de Pago"
        verbose_name_plural = "Tipos de Medios de Pago"
        ordering = ("-activo", "nombre")
