import json
from django import forms
from .models import EmisorFacturaElectronica

class EmisorFacturaElectronicaForm(forms.ModelForm):
    class Meta:
        model = EmisorFacturaElectronica
        fields = [
            'nombre', 'ruc', 'dv_ruc', 'email_emisor', 'direccion', 'numero_casa',
            'codigo_departamento', 'descripcion_departamento', 'codigo_ciudad',
            'descripcion_ciudad', 'telefono', 'establecimiento', 'punto_expedicion',
            'email_equipo', 'rango_numeracion_inicio', 'rango_numeracion_fin',
            'siguiente_numero_factura', 'actividades_economicas'
        ]
        widgets = {
            'actividades_economicas': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'actividades_economicas': 'Ingrese un JSON válido para las actividades económicas. Ejemplo: [{"cActEco": "46699", "dDesActEco": "Comercio al por mayor..."}]',
        }

    def clean(self):
        cleaned_data = super().clean()
        rango_inicio = cleaned_data.get('rango_numeracion_inicio')
        rango_fin = cleaned_data.get('rango_numeracion_fin')
        siguiente_numero = cleaned_data.get('siguiente_numero_factura')

        if rango_inicio is not None and rango_fin is not None:
            if rango_inicio >= rango_fin:
                self.add_error('rango_numeracion_fin', "El fin del rango debe ser mayor que el inicio.")
            
            if siguiente_numero is not None:
                if not (rango_inicio <= siguiente_numero <= rango_fin):
                    self.add_error('siguiente_numero_factura', "El siguiente número de factura debe estar dentro del rango definido.")
        
        return cleaned_data
