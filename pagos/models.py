from django.db import models
# Tipos de comisiones y tarifas que pueden aplicar a los medios de pago/billeteras:

# Comisión porcentual:
# Se aplica un porcentaje sobre el monto de la transacción.
# Ejemplo: 2% por cada pago enviado con la billetera.

# Comisión fija:
# Se aplica un monto fijo por cada transacción, independientemente del valor.
# Ejemplo: 5000 PYG por operación.

# Bonificaciones o descuentos:
# Algunas billeteras pueden ofrecer incentivos por uso frecuente
# o para ciertos tipos de transacción.

# Tarifa por retiro o transferencia:
# Si el usuario quiere mover dinero de la billetera a una cuenta bancaria,
# podría aplicarse una tarifa adicional.

class TipoMedioPago(models.Model):
    """
    Tipos de medio de pago: Billetera Electrónica, Tarjeta, Cheque, etc.
    """
    nombre = models.CharField(max_length=50, unique=True)
    comision_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    comision_monto_fijo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bonificacion_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    # Definición de tipos de medio de pago y su relación con bonificaciones:
# "Billetera Electrónica": es_cuenta_bancaria = False
# Esto indica al sistema que, cuando un cliente use este método, se aplicará la bonificación correspondiente en el futuro.

# "Transferencia Bancaria": es_cuenta_bancaria = True
# Esto indica al sistema que, si el cliente utiliza este método, la bonificación configurada no debe aplicarse.

    es_cuenta_bancaria = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre
