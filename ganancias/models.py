"""
Modelos de la aplicación **ganancias**.

.. module:: ganancias.models
   :synopsis: Registros de ganancias por transacción de divisas.

Este módulo define:

- :class:`RegistroGanancia`: Almacena la ganancia neta obtenida por cada
  :class:`transacciones.models.Transaccion`, expresada en una moneda base
  (normalmente PYG) y asociada a la moneda extranjera operada.
"""


from django.db import models
from transacciones.models import Transaccion
from monedas.models import Moneda

class RegistroGanancia(models.Model):

    """
    Registro de la ganancia neta asociada a una transacción de compra/venta.

    Cada instancia representa el resultado económico de una
    :class:`transacciones.models.Transaccion`, calculado a partir de la
    comisión efectiva aplicada y el monto operado.

    Campos principales
    ------------------
    - ``transaccion``: Llave primaria y relación 1:1 con la transacción origen.
    - ``ganancia_registrada``: Monto de la ganancia neta en ``moneda_ganancia``.
    - ``moneda_ganancia``: Moneda en la que se registra la ganancia
      (por conveniencia suele ser PYG).
    - ``moneda_operada``: Moneda extranjera involucrada en la operación
      (por ejemplo USD, EUR).
    - ``fecha_registro``: Fecha y hora en la que se calculó/registró la ganancia.

    Este modelo se crea o actualiza automáticamente desde
    :mod:`ganancias.signals` cuando una transacción pasa al estado
    ``completada``.
    """
    
    transaccion = models.OneToOneField(
        Transaccion,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='registro_ganancia'
    )
    ganancia_registrada = models.DecimalField(max_digits=15, decimal_places=2)
    moneda_ganancia = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name='ganancias_en_pyg',
        help_text="Moneda en la que se registra la ganancia (ej. PYG)."
    )
    moneda_operada = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name='ganancias_por_moneda',
        help_text="Moneda extranjera de la transacción (ej. USD, EUR)."
    )
    fecha_registro = models.DateTimeField(db_index=True)

    def __str__(self):
        return f"Ganancia para Transacción {self.transaccion.id}: {self.ganancia_registrada} {self.moneda_ganancia.codigo} (Operada: {self.moneda_operada.codigo})"

    class Meta:
        verbose_name = "Registro de Ganancia"
        verbose_name_plural = "Registros de Ganancias"
        ordering = ['-fecha_registro']
