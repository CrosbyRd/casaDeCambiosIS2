from django.db import models
# Tipos de comisiones y tarifas que pueden aplicar a los medios de pago/billeteras:

# Comisión porcentual:
# Se aplica un porcentaje sobre el monto de la transacción.
# Ejemplo: 2% por cada pago enviado con la billetera.


# Bonificaciones o descuentos:
# Algunas billeteras pueden ofrecer incentivos por uso frecuente
# o para ciertos tipos de transacción.

# Tarifa por retiro o transferencia:
# Si el usuario quiere mover dinero de la billetera a una cuenta bancaria,
# podría aplicarse una tarifa adicional.

class TipoMedioPago(models.Model):
    """
    Define los tipos de medios de pago, como 'Billetera Electrónica',
    'Tarjeta de Crédito', 'Cheque', etc.
    """
    nombre = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Ej. 'Billetera Electrónica', 'Tarjeta de Crédito'"
    )
    comision_porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00, 
        help_text="Comisión en % del monto total de la transacción"
    )
    es_cuenta_bancaria = models.BooleanField(
        default=False, 
        help_text="Indica si es una cuenta bancaria (no se aplican bonificaciones)."
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de Medio de Pago"
        verbose_name_plural = "Tipos de Medios de Pago"
