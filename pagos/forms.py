from django import forms
from .models import TipoMedioPago

class TipoMedioPagoForm(forms.ModelForm):
    class Meta:
        model = TipoMedioPago
        fields = ['nombre', 'comision_porcentaje', 'comision_monto_fijo', 'bonificacion_porcentaje', 'es_cuenta_bancaria']
