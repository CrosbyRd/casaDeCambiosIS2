from django import forms
from .models import CategoriaMedio

class CategoriaMedioForm(forms.ModelForm):
    class Meta:
        model = CategoriaMedio
        fields = [
            "nombre",
            "codigo",
            "moneda_predeterminada",
            "requiere_datos_extra",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "moneda_predeterminada": forms.TextInput(attrs={"class": "form-control"}),
        }
