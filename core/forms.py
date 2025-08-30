# core/forms.py
from django import forms
from .simulacion_data import COTIZACIONES_SIMULADAS

# Generamos las opciones para los selects de forma dinámica
# Esto es genial porque si añades una moneda a simulacion_data, aparece aquí automáticamente
MONEDAS_CHOICES = [('PYG', 'Guaraní')] + [(codigo, data['nombre']) for codigo, data in COTIZACIONES_SIMULADAS.items()]

class SimulacionForm(forms.Form):
    monto = forms.DecimalField(
        label="Monto a cambiar",
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1.000.000'})
    )
    moneda_origen = forms.ChoiceField(
        choices=MONEDAS_CHOICES,
        label="Moneda que tengo",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    moneda_destino = forms.ChoiceField(
        choices=MONEDAS_CHOICES,
        label="Moneda que quiero",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        # La lógica de validación sigue siendo la misma y es crucial
        cleaned_data = super().clean()
        origen = cleaned_data.get("moneda_origen")
        destino = cleaned_data.get("moneda_destino")

        if origen and destino:
            if origen == destino:
                raise forms.ValidationError("Las monedas no pueden ser iguales.")
            if origen != 'PYG' and destino != 'PYG':
                raise forms.ValidationError("La simulación debe involucrar Guaraníes (PYG).")
        return cleaned_data