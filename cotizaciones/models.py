from django.db import models
from monedas.models import Moneda
from django.core.validators import MinValueValidator
from django.utils import timezone
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
        self.__original_comision_venta = self.comision_venta
        self.__original_valor_compra = self.valor_compra
        self.__original_comision_compra = self.comision_compra

    def save(self, *args, **kwargs):
        # Lógica para detectar cambio y enviar señal
        super().save(*args, **kwargs) # Guardar primero
        
        # Un cambio en la venta ocurre si el valor base O la comisión cambian.
        venta_cambio = (self.valor_venta != self.__original_valor_venta or 
                        self.comision_venta != self.__original_comision_venta)
        
        # Un cambio en la compra ocurre si el valor base O la comisión cambian.
        compra_cambio = (self.valor_compra != self.__original_valor_compra or
                         self.comision_compra != self.__original_comision_compra)

        if venta_cambio or compra_cambio:
            from .signals import cotizacion_actualizada
            cotizacion_actualizada.send(
                sender=self.__class__,
                instance=self,
                venta_cambio=venta_cambio,
                compra_cambio=compra_cambio
            )
class CotizacionHistorica(models.Model):
    moneda_base = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='hist_base')
    moneda_destino = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='hist_destino')

    valor_compra = models.DecimalField(max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
    comision_compra = models.DecimalField(max_digits=10, decimal_places=4, default=0, validators=[MinValueValidator(0)])
    valor_venta = models.DecimalField(max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
    comision_venta = models.DecimalField(max_digits=10, decimal_places=4, default=0, validators=[MinValueValidator(0)])

    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    fuente = models.CharField(max_length=40, blank=True, default="")  # opcional: "manual", "api", etc.

    class Meta:
        indexes = [
            models.Index(fields=["moneda_base", "moneda_destino", "fecha"], name="idx_hist_pair_fecha"),
        ]
        verbose_name = "Cotización histórica"
        verbose_name_plural = "Cotizaciones históricas"

    def __str__(self):
        return f"{self.moneda_base.codigo}->{self.moneda_destino.codigo} @ {self.fecha:%Y-%m-%d %H:%M}"