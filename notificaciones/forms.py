# notificaciones/forms.py (NUEVO ARCHIVO)
from django import forms
from .models import PreferenciasNotificacion
from monedas.models import Moneda

class PreferenciasNotificacionForm(forms.ModelForm):
    monedas_seguidas = forms.ModelMultipleChoiceField(
        queryset=Moneda.objects.filter(admite_en_linea=True).exclude(codigo='PYG'),
        widget=forms.CheckboxSelectMultiple,
        label="Recibir notificaciones para estas monedas",
        required=False
    )

    class Meta:
        model = PreferenciasNotificacion
        fields = ['recibir_email_tasa_cambio', 'monedas_seguidas']
        labels = {
            'recibir_email_tasa_cambio': "Recibir alertas de cambio de tasa por correo electrónico"
        }
