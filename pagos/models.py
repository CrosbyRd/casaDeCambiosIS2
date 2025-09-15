from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

#NUEVO
from django.core.exceptions import ValidationError
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
    def clean(self):
        # Validar nombre
        if not self.nombre:
            raise ValidationError({'nombre': "El nombre no puede estar vacío."})

        # Validar comisiones
        if self.comision_porcentaje < 0 or self.comision_porcentaje > 100:
            raise ValidationError({'comision_porcentaje': "Debe estar entre 0 y 100."})

        if self.bonificacion_porcentaje < 0 or self.bonificacion_porcentaje > 100:
            raise ValidationError({'bonificacion_porcentaje': "Debe estar entre 0 y 100."})

    def save(self, *args, **kwargs):
        # Llamar a clean antes de guardar para validar
        self.full_clean()
        super().save(*args, **kwargs)
