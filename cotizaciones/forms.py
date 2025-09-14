from django import forms
from .models import Cotizacion

class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = [
            'moneda_destino',
            'valor_compra',
            'valor_venta',
            'comision_compra',
            'comision_venta',
        ]
        widgets = {
            'moneda_destino': forms.Select(attrs={'class': 'form-select'}),
            'valor_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'valor_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'comision_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'comision_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }

    def clean(self):
        cleaned = super().clean()
        for k in ('valor_compra', 'valor_venta', 'comision_compra', 'comision_venta'):
            v = cleaned.get(k)
            if v is not None and v < 0:
                self.add_error(k, "No puede ser negativo.")
        return cleaned
