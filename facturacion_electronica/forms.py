from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import EmisorFacturaElectronica


class EmisorFacturaElectronicaForm(forms.ModelForm):
    """
    Form para crear/editar EmisorFacturaElectronica alineado al XML:
    - Contacto: usa email_emisor / telefono (nombres del modelo)
    - Actividades: permite CSV -> lista, validando 5 o 6 dígitos (cActEco)
    - Muestra numeración 401–450 y siguiente número (con min/max)
    - Token visible (solo lectura) para diagnóstico
    """

    # Carga cómoda de múltiples cActEco (CSV)
    actividades_economicas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Ej.: 62010,74909  (admite 5 o 6 dígitos por código)"
        }),
        help_text=(
            "Ingrese las actividades adicionales separadas por comas. "
            "Cada código cActEco debe tener 5 o 6 dígitos (según catastro vigente)."
        ),
        label="Actividades Económicas adicionales (cActEco)"
    )

    # Token: solo lectura para no tocar desde el form (útil para ver si hay sesión)
    auth_token = forms.CharField(
        required=False,
        label="Token de autenticación (FacturaSegura)",
        widget=forms.TextInput(attrs={"readonly": "readonly"})
    )
    token_generado_at = forms.DateTimeField(
        required=False,
        label="Token generado el",
        widget=forms.DateTimeInput(attrs={"readonly": "readonly"})
    )

    class Meta:
        model = EmisorFacturaElectronica
        fields = [
            # Identificación
            "nombre", "ruc", "dv_ruc",
            # Contacto (nombres REALES del modelo)
            "email_emisor", "telefono",
            # Dirección
            "codigo_departamento", "descripcion_departamento",
            "codigo_ciudad", "descripcion_ciudad",
            "direccion", "numero_casa", "pais",
            # Numeración fija (Estab/Punto)
            "establecimiento", "punto_expedicion",
            # Timbrado
            "numero_timbrado_actual", "fecha_inicio_timbrado",
            # Actividades
            "actividad_economica_principal", "actividades_economicas",
            # Estado
            "activo",
            # Rango y correlativo
            "rango_numeracion_inicio", "rango_numeracion_fin", "siguiente_numero_factura",
            # Token FS (solo lectura)
            "auth_token", "token_generado_at",
        ]
        widgets = {
            "fecha_inicio_timbrado": forms.DateInput(attrs={"type": "date"}),
            "rango_numeracion_inicio": forms.NumberInput(attrs={"min": 401, "max": 450}),
            "rango_numeracion_fin": forms.NumberInput(attrs={"min": 401, "max": 450}),
            "siguiente_numero_factura": forms.NumberInput(attrs={"min": 401, "max": 450}),
        }
        help_texts = {
            "numero_timbrado_actual": "8 dígitos. Ej.: 02595733",
            "establecimiento": "3 dígitos. Ej.: 001",
            "punto_expedicion": "3 dígitos. Ej.: 003",
            "actividad_economica_principal": "Código cActEco de 5 o 6 dígitos. Ej.: 62010",
            "rango_numeracion_inicio": "Inicio del rango del equipo (por ej., 401).",
            "rango_numeracion_fin": "Fin del rango del equipo (por ej., 450).",
            "siguiente_numero_factura": "Correlativo a emitir (se sugiere no modificar manualmente).",
        }

    # === Inicialización: poblar el textarea de actividades desde la lista JSON ===
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si hay instancia existente, mostrar la lista como CSV
        inst = getattr(self, "instance", None)
        if inst and inst.pk and isinstance(inst.actividades_economicas, list):
            self.fields["actividades_economicas"].initial = ", ".join(inst.actividades_economicas)

        # Estética: opcional, marcar 'auth_token' y 'token_generado_at' como deshabilitados
        self.fields["auth_token"].widget.attrs["readonly"] = "readonly"
        self.fields["token_generado_at"].widget.attrs["readonly"] = "readonly"

    # === Validaciones específicas ===

    def clean_actividad_economica_principal(self):
        """
        Acepta 5 o 6 dígitos (el XML del profe trae 5 dígitos, ej.: 62010).
        Cambia a ==6 si querés forzar 6 dígitos.
        """
        val = (self.cleaned_data.get("actividad_economica_principal") or "").strip()
        if val:
            if not (val.isdigit() and len(val) in (5, 6)):
                raise ValidationError(_("La actividad económica principal debe tener 5 o 6 dígitos numéricos."))
        return val

    def clean_actividades_economicas(self):
        """
        Acepta CSV y lo transforma a lista de strings de 5 o 6 dígitos.
        """
        raw = (self.cleaned_data.get("actividades_economicas") or "").strip()
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for code in parts:
            if not (code.isdigit() and len(code) in (5, 6)):
                raise ValidationError(_("Cada actividad económica debe tener 5 o 6 dígitos numéricos."))
        return parts

    def clean(self):
        cleaned = super().clean()

        # Estab/Punto/Timbrado en formato fijo
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

        # Rango 401–450 y siguiente
        r_ini = cleaned.get("rango_numeracion_inicio")
        r_fin = cleaned.get("rango_numeracion_fin")
        nxt = cleaned.get("siguiente_numero_factura")
        if r_ini is not None and r_fin is not None and r_ini > r_fin:
            self.add_error("rango_numeracion_inicio", _("El inicio no puede ser mayor que el fin."))
            self.add_error("rango_numeracion_fin", _("El fin no puede ser menor que el inicio."))
        if nxt is not None and r_ini is not None and r_fin is not None:
            if not (r_ini <= nxt <= r_fin):
                self.add_error("siguiente_numero_factura", _("Debe estar dentro del rango definido."))

        return cleaned

    # Guardar: el ModelForm ya setea el campo JSON, pero si quisieras
    # convertir manualmente, aquí tendrías control adicional.
    # def save(self, commit=True):
    #     obj = super().save(commit=False)
    #     # obj.actividades_economicas = self.cleaned_data["actividades_economicas"]  # ya lo hace el form
    #     if commit:
    #         obj.save()
    #     return obj
