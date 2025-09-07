from django.db import models
from monedas.models import Moneda

class Cotizacion(models.Model):
    moneda_base = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='cotizaciones_base')
    moneda_destino = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='cotizaciones_destino')
    valor_compra = models.DecimalField(max_digits=10, decimal_places=4)
    valor_venta = models.DecimalField(max_digits=10, decimal_places=4)
    comision_compra = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    comision_venta = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('moneda_base', 'moneda_destino')

    def __str__(self):
        return f"{self.moneda_base.codigo} a {self.moneda_destino.codigo}"
    
    @property
    def total_compra(self):
        return self.valor_compra + self.comision_compra
    
    @property
    def total_venta(self):
        return self.valor_venta + self.comision_venta