from django.db import models
from transacciones.models import Transaccion
from monedas.models import Moneda

class RegistroGanancia(models.Model):
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
    fecha_registro = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Ganancia para Transacción {self.transaccion.id}: {self.ganancia_registrada} {self.moneda_ganancia.codigo} (Operada: {self.moneda_operada.codigo})"

    class Meta:
        verbose_name = "Registro de Ganancia"
        verbose_name_plural = "Registros de Ganancias"
        ordering = ['-fecha_registro']
