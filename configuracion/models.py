"""
Modelos de la aplicación **configuracion**.

.. module:: configuracion.models
   :synopsis: Define los modelos para límites transaccionales.

Incluye modelos relacionados con la configuración de límites diarios y mensuales
por moneda, vinculados a la moneda base del sistema.
"""
from django.db import models
from monedas.models import Moneda

def get_moneda_base():
    """
    Devuelve la moneda base del sistema (PYG).

    Se usa como valor por defecto en TransactionLimit.
    """
    # Trae la moneda base PYG
    return Moneda.objects.get(codigo='PYG')

class TransactionLimit(models.Model):
    """
    Modelo que representa un límite de transacción por moneda.

    Permite definir límites diarios y mensuales para transacciones,
    con opciones de habilitación/deshabilitación para cada tipo.

    **Campos**
    ----------
    moneda : ForeignKey
        Moneda asociada al límite. Por defecto es la moneda base 'PYG'.
        No editable desde el admin.
    aplica_diario : BooleanField
        Indica si aplica límite diario.
    monto_diario : DecimalField
        Monto máximo permitido diario.
    aplica_mensual : BooleanField
        Indica si aplica límite mensual.
    monto_mensual : DecimalField
        Monto máximo permitido mensual.
    """
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
        """
        Representación legible del límite de transacción.

        Devuelve la moneda y los montos habilitados, por ejemplo:
        "PYG (Diario: 100000, Mensual: 500000)"
        """
        tipos = []
        if self.aplica_diario:
            tipos.append(f"Diario: {self.monto_diario}")
        if self.aplica_mensual:
            tipos.append(f"Mensual: {self.monto_mensual}")
        return f"{self.moneda.codigo} ({', '.join(tipos)})"
