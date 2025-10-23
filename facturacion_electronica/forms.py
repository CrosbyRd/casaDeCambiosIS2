import json
from django import forms
from .models import EmisorFacturaElectronica
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class EmisorFacturaElectronicaForm(forms.ModelForm):
    """
    Form para crear/editar EmisorFacturaElectronica con validaciones
    alineadas al XML de ejemplo del profesor (timbrado, establecimiento,
    punto de expedición y cActEco).
    """

    # Campo de ayuda para cargar múltiples cActEco de forma cómoda
    actividades_economicas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: 620100,620900"}),
        help_text=(
            "Ingrese las actividades adicionales como una lista separada por comas "
            "(solo los códigos cActEco de 6 dígitos). Ej.: 620100,620900"
        ),
        label="Actividades Económicas adicionales (cActEco)"
    )

    class Meta:
        model = EmisorFacturaElectronica
        fields = [
            # Identificación
            "nombre", "ruc", "dv_ruc",
            # Contacto
            "email_contacto", "telefono_contacto",
            # Dirección
            "codigo_departamento", "descripcion_departamento",
            "codigo_ciudad", "descripcion_ciudad",
            "direccion", "numero_casa", "pais",
            # Numeración fija
            "establecimiento", "punto_expedicion",
            # Timbrado
            "numero_timbrado_actual", "fecha_inicio_timbrado",
            # Actividades
            "actividad_economica_principal", "actividades_economicas",
            # Estado
            "activo",
        ]
        widgets = {
            "fecha_inicio_timbrado": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "numero_timbrado_actual": "8 dígitos. Ej.: 02595733",
            "establecimiento": "3 dígitos. Ej.: 001",
            "punto_expedicion": "3 dígitos. Ej.: 003",
            "actividad_economica_principal": "Código cActEco de 6 dígitos. Ej.: 620100",
        }

    def clean_actividad_economica_principal(self):
        val = self.cleaned_data.get("actividad_economica_principal", "") or ""
        if val:
            if not (val.isdigit() and len(val) == 6):
                raise ValidationError(_("La actividad económica principal debe ser un código numérico de 6 dígitos."))
        return val

    def clean_actividades_economicas(self):
        """
        Acepta una cadena separada por comas y la convierte a lista de strings de 6 dígitos.
        """
        raw = self.cleaned_data.get("actividades_economicas", "") or ""
        raw = raw.strip()
        if not raw:
            return []

        # Separar por coma y normalizar espacios
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for code in parts:
            if not (code.isdigit() and len(code) == 6):
                raise ValidationError(_("Cada actividad económica debe ser un código numérico de 6 dígitos."))
        return parts

    def clean(self):
        cleaned = super().clean()

        # Coherencia básica entre establecimiento/punto/timbrado
        est = cleaned.get("establecimiento")
        pto = cleaned.get("punto_expedicion")
        tim = cleaned.get("numero_timbrado_actual")

        if est and (not est.isdigit() or len(est) != 3):
            self.add_error("establecimiento", _("Debe tener 3 dígitos."))
        if pto and (not pto.isdigit() or len(pto) != 3):
            self.add_error("punto_expedicion", _("Debe tener 3 dígitos."))
        if tim and (not tim.isdigit() or len(tim) != 8):
            self.add_error("numero_timbrado_actual", _("Debe tener exactamente 8 dígitos."))

        # RUC/DV
        ruc = cleaned.get("ruc")
        dv = cleaned.get("dv_ruc")
        if ruc and (not ruc.isdigit() or not (7 <= len(ruc) <= 8)):
            self.add_error("ruc", _("El RUC debe ser numérico de 7 u 8 dígitos."))
        if dv and (not dv.isdigit() or len(dv) != 1):
            self.add_error("dv_ruc", _("El DV debe ser un único dígito."))

        return cleaned