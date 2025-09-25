from django.db import models
from monedas.models import Moneda

def get_moneda_base():
    # Trae la moneda base PYG
    return Moneda.objects.get(codigo='PYG')

class TransactionLimit(models.Model):
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.CASCADE,
        default=get_moneda_base,
        editable=False
    )
    aplica_diario = models.BooleanField(default=True)
    monto_diario = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    aplica_mensual = models.BooleanField(default=False)
    monto_mensual = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Límite de Transacción"
        verbose_name_plural = "Límites de Transacción"

    def __str__(self):
        tipos = []
        if self.aplica_diario:
            tipos.append(f"Diario: {self.monto_diario}")
        if self.aplica_mensual:
            tipos.append(f"Mensual: {self.monto_mensual}")
        return f"{self.moneda.codigo} ({', '.join(tipos)})"
