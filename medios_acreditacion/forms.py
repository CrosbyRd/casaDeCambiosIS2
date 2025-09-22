# medios_acreditacion/forms.py
from django import forms
from .models import CategoriaMedio

class CategoriaMedioForm(forms.ModelForm):
    class Meta:
        model = CategoriaMedio
        fields = [
            "codigo",               # select con: transferencia / billetera / pickup
            "requiere_datos_extra",
            "activo",
        ]
        widgets = {
            "codigo": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "codigo": "Código (tipo de medio)",
            "requiere_datos_extra": "Requiere datos extra",
            "activo": "Activo",
        }
