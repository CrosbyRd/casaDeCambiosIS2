# notificaciones/forms.py (NUEVO ARCHIVO)

"""
Módulo de formularios para el manejo de las preferencias de notificación.

Contiene el formulario que permite a los usuarios configurar sus opciones
de alertas por correo electrónico y seleccionar las monedas para las cuales
desean recibir notificaciones automáticas.
"""
from django import forms
from .models import PreferenciasNotificacion
from monedas.models import Moneda

class PreferenciasNotificacionForm(forms.ModelForm):
    """
    Formulario para la gestión de las **preferencias de notificación** del usuario.

    Permite definir si el usuario desea recibir alertas por correo electrónico
    sobre variaciones en las tasas de cambio y seleccionar las monedas de su interés.

    :cvar monedas_seguidas: Campo de selección múltiple para elegir monedas
        que el usuario desea seguir (solo monedas con `admite_en_linea=True`
        y diferentes del guaraní paraguayo `'PYG'`).
    :type monedas_seguidas: django.forms.ModelMultipleChoiceField

    :cvar Meta: Configuración de metadatos del formulario que asocia el modelo
        y define las etiquetas de los campos.
    :type Meta: type
    """
    monedas_seguidas = forms.ModelMultipleChoiceField(
        queryset=Moneda.objects.filter(admite_en_linea=True).exclude(codigo='PYG'),
        widget=forms.CheckboxSelectMultiple,
        label="Recibir notificaciones para estas monedas",
        required=False
    )

    class Meta:
        """
        Clase interna que define los metadatos del formulario.

        :cvar model: Modelo al cual está vinculado el formulario.
        :type model: notificaciones.models.PreferenciasNotificacion
        :cvar fields: Campos del modelo incluidos en el formulario.
        :type fields: list[str]
        :cvar labels: Etiquetas personalizadas para los campos.
        :type labels: dict
        """
        model = PreferenciasNotificacion
        fields = ['recibir_email_tasa_cambio', 'monedas_seguidas']
        labels = {
            'recibir_email_tasa_cambio': "Recibir alertas de cambio de tasa por correo electrónico"
        }
