from django import forms
from .models import TipoMedioPago

class TipoMedioPagoForm(forms.ModelForm):
    class Meta:
        model = TipoMedioPago
        fields = [
            'nombre',
            'comision_porcentaje',
            'bonificacion_porcentaje',  # ← nuevo
            'activo',                   # ← ya lo añadimos antes
        ]
