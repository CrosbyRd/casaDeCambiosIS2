from django.db import models

from monedas.models import Moneda 

class Cotizacion(models.Model):
    moneda_base = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='cotizaciones_base')
    moneda_destino = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='cotizaciones_destino')
    valor_compra = models.DecimalField(max_digits=10, decimal_places=4)
    valor_venta = models.DecimalField(max_digits=10, decimal_places=4)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('moneda_base', 'moneda_destino')
        permissions = [
            ("access_cotizaciones", "Puede acceder a la sección de cotizaciones"),
        ]
    
    def __str__(self):
        return f"{self.moneda_base.codigo} a {self.moneda_destino.codigo}"
