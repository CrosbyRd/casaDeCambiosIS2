from django import forms
from django.forms import widgets
from .models import TipoMedioPago, CampoMedioPago, MedioPagoCliente
import re

# ------------------------------
# Admin: Tipo + Campos (inline)
# ------------------------------
class TipoMedioPagoForm(forms.ModelForm):
    class Meta:
        model = TipoMedioPago
        fields = ["nombre", "comision_porcentaje", "descripcion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input w-full"}),
            "comision_porcentaje": forms.NumberInput(attrs={
                "class": "flex-1 px-3 py-2 border-0 focus:outline-none",  # ← las que querías
                "step": "0.01", "min": "0", "max": "100", "inputmode": "decimal",
            }),
            "descripcion": forms.Textarea(attrs={"class": "form-textarea w-full", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

class CampoMedioPagoForm(forms.ModelForm):
    class Meta:
        model = CampoMedioPago
        fields = [
            "nombre_campo",
            "tipo_dato",
            "obligatorio",
            "regex_opcional",
            "regex_personalizado",
            "activo",
        ]
        widgets = {
            "nombre_campo": forms.TextInput(attrs={"class": "form-input w-full"}),
            "tipo_dato": forms.Select(attrs={"class": "form-select w-full"}),
            "obligatorio": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "regex_opcional": forms.Select(attrs={"class": "form-select w-full"}),
            "regex_personalizado": forms.TextInput(attrs={"class": "form-input w-full", "placeholder": r"^...$"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

# ---------------------------------
# Cliente: Form dinámico por "tipo"
# ---------------------------------
class MedioPagoClienteForm(forms.ModelForm):
    tipo = forms.ModelChoiceField(
        queryset=TipoMedioPago.objects.filter(activo=True),
        widget=forms.Select(attrs={"class": "form-select w-full"}),
        help_text="Selecciona el tipo de medio de pago",
    )

    class Meta:
        model = MedioPagoCliente
        fields = ["tipo", "alias", "activo", "predeterminado"]
        widgets = {
            "alias": forms.TextInput(attrs={"class": "form-input w-full"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "predeterminado": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

 
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Nunca accedas a self.instance.tipo directamente si no hay FK
        tipo = None
        # Si estamos editando y hay FK asignado
        if getattr(self.instance, "pk", None) and getattr(self.instance, "tipo_id", None):
            tipo = self.instance.tipo
        else:
            # Intentar tomarlo del POST o del initial (p.ej. ?tipo=<uuid>)
            tipo_pk = self.data.get("tipo") or self.initial.get("tipo")
            if tipo_pk:
                try:
                    tipo = TipoMedioPago.objects.get(pk=tipo_pk)
                except TipoMedioPago.DoesNotExist:
                    tipo = None

        self._campos_config = []
        if tipo:
            for campo in tipo.campos.filter(activo=True):
                nombre = campo.nombre_campo
                requerido = campo.obligatorio
                self.fields[nombre] = forms.CharField(
                    label=nombre,
                    required=requerido,
                    widget=forms.TextInput(attrs={"class": "form-input w-full"}),
                )
                # Si es edición, prellenar
                if getattr(self.instance, "pk", None):
                    self.fields[nombre].initial = (self.instance.datos or {}).get(nombre, "")
                self._campos_config.append(campo)

    def clean(self):
        cleaned = super().clean()
        datos = {}
        errores = {}

        def check_regex(patron, valor):
            if not patron:
                return True
            try:
                return re.fullmatch(patron, str(valor)) is not None
            except re.error:
                return False

        for campo in getattr(self, "_campos_config", []):
            nombre = campo.nombre_campo
            valor = self.cleaned_data.get(nombre)

            # Validación por tipo de dato liviana (se alinea con models.clean())
            if valor not in (None, ""):
                if campo.tipo_dato == CampoMedioPago.TipoDato.NUMERO and not re.fullmatch(r"^-?\d+(?:[\.,]\d+)?$", str(valor)):
                    errores[nombre] = "Debe ser numérico"
                elif campo.tipo_dato == CampoMedioPago.TipoDato.TELEFONO and not re.fullmatch(r"^\+?\d{6,15}$", str(valor)):
                    errores[nombre] = "Teléfono inválido"
                elif campo.tipo_dato == CampoMedioPago.TipoDato.EMAIL and not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(valor)):
                    errores[nombre] = "Email inválido"
                elif campo.tipo_dato == CampoMedioPago.TipoDato.RUC and not re.fullmatch(r"^\d{6,8}-\d{1}$", str(valor)):
                    errores[nombre] = "RUC inválido (########-#)"

            # Regex opcional o personalizada
            patron = campo.regex_personalizado or campo.regex_opcional or ""
            if valor not in (None, "") and patron and not check_regex(patron, valor):
                errores[nombre] = "Formato inválido"

            datos[nombre] = valor

        if errores:
            raise forms.ValidationError(errores)

        self.instance.datos = datos
        return cleaned
    
    @property
    def campos_config(self):
        return getattr(self, "_campos_config", [])