from django.db import models
from monedas.models import Moneda
from django.core.validators import MinValueValidator
class Cotizacion(models.Model):
    moneda_base = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='cotizaciones_base')
    moneda_destino = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='cotizaciones_destino')
    valor_compra = models.DecimalField(max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
    valor_venta = models.DecimalField(max_digits=10, decimal_places=4,validators=[MinValueValidator(0)])
    comision_compra = models.DecimalField(max_digits=10, decimal_places=4, default=0, validators=[MinValueValidator(0)])
    comision_venta = models.DecimalField(max_digits=10, decimal_places=4, default=0, validators=[MinValueValidator(0)])
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('moneda_base', 'moneda_destino')

        permissions = [
            ("access_cotizaciones", "Puede acceder a la sección de cotizaciones"),
        ]
    

    def __str__(self):
        return f"{self.moneda_base.codigo} a {self.moneda_destino.codigo}"
    
    @property
    def total_compra(self):
        # La casa de cambios compra la divisa al cliente, la comisión se resta del valor base.
        return self.valor_compra - self.comision_compra
    
    @property
    def total_venta(self):
        # La casa de cambios vende la divisa al cliente, la comisión se suma al valor base.
        return self.valor_venta + self.comision_venta

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Guardar los valores originales para comparar en save()
        self.__original_valor_venta = self.valor_venta
        self.__original_valor_compra = self.valor_compra

    def save(self, *args, **kwargs):
        # Lógica para detectar cambio y enviar señal
        super().save(*args, **kwargs) # Guardar primero
        
        venta_cambio = self.valor_venta != self.__original_valor_venta
        compra_cambio = self.valor_compra != self.__original_valor_compra

        if venta_cambio or compra_cambio:
            from .signals import cotizacion_actualizada
            cotizacion_actualizada.send(
                sender=self.__class__,
                instance=self,
                venta_cambio=venta_cambio,
                compra_cambio=compra_cambio
            )
