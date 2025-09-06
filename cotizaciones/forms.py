from django import forms
from .models import Moneda, Cotizacion


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['moneda_destino', 'valor_compra', 'valor_venta']  # moneda_base no se muestra
