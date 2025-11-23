from django import forms
from .models import Cotizacion

class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['moneda_destino', 'valor_compra', 'valor_venta', 'comision_compra', 'comision_venta']
        widgets = {
            'moneda_destino': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'cargarValoresBase(this)'
            }),
            'valor_compra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'onchange': 'calcularTotales()'
            }),
            'valor_venta': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.0001',
                'onchange': 'calcularTotales()'
            }),
            'comision_compra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'onchange': 'calcularTotales()'
            }),
            'comision_venta': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001', 
                'onchange': 'calcularTotales()'
            }),
        }