from django import forms
from django.forms import widgets
from django.forms import inlineformset_factory, BaseInlineFormSet  # 👈 AÑADIDO
from .models import TipoMedioPago, CampoMedioPago, MedioPagoCliente
import re


# Presets de regex (value=regex, label=texto que ve el admin)
REGEX_PREDEF_CHOICES = [
    ("", "(sin regex)"),
    (r"^\d+$", "Solo números"),
    (r"^[^@\s]+@[^@\s]+\.[^@\s]+$", "Email básico"),      # ← igual al modelo
    (r"^09\d{8}$", "Teléfono PY (09xxxxxxxx)"),
    (r"^\d{6,8}-\d{1}$", "RUC"),
    (r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+$", "Solo letras"),
]


# ------------------------------
# Admin: Tipo + Campos (inline)
# ------------------------------
class TipoMedioPagoForm(forms.ModelForm):
    class Meta:
        model = TipoMedioPago
        fields = ["nombre", "comision_porcentaje", "descripcion", "activo", "engine", "engine_config"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input w-full"}),
            "comision_porcentaje": forms.NumberInput(attrs={
                "class": "flex-1 px-3 py-2 border-0 focus:outline-none",
                "step": "0.01", "min": "0", "max": "100", "inputmode": "decimal",
            }),
            "descripcion": forms.Textarea(attrs={"class": "form-textarea w-full", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "engine": forms.Select(attrs={"class": "form-select w-full"}),
        }

class CampoMedioPagoForm(forms.ModelForm):
    """
    ModelForm del campo: NO incluye ni el PK (id_campo) ni la FK (tipo).
    Eso lo maneja el formset con instance=self.object.
    """
    class Meta:
        model = CampoMedioPago
        fields = [
            "nombre_campo",
            "tipo_dato",
            "obligatorio",
            "regex_opcional",
            "activo",
        ]
        widgets = {
            "nombre_campo": forms.TextInput(attrs={"class": "form-input w-full"}),
            "tipo_dato": forms.Select(attrs={"class": "form-select w-full"}),
            "obligatorio": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "regex_opcional": forms.Select(attrs={"class": "form-select w-full"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 👉 aseguramos que el select muestre nuestros presets y guarde el patrón
        self.fields["regex_opcional"].choices = REGEX_PREDEF_CHOICES


class _BaseCampoMedioPagoFormSet(BaseInlineFormSet):
    """
    - extra=0: no crea líneas vacías “fantasma”.
    - can_delete=True: habilita {{ f.DELETE }}.
    - clean(): valida duplicados por 'nombre_campo' entre formularios no eliminados.
    """
    def clean(self):
        super().clean()
        seen = set()
        errors = {}
        for form in self.forms:
            # Saltar forms vacíos o marcados para borrar
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("nombre_campo") in (None, ""):
                # si el form no tiene nombre, dejemos que falle por “obligatorio”
                # (o simplemente ignoramos para no duplicar mensajes)
                continue

            key = form.cleaned_data["nombre_campo"].strip().lower()
            if key in seen:
                form.add_error("nombre_campo", "Ya existe otro campo con ese nombre.")
                errors["__all__"] = "Hay campos duplicados en el formulario."
            else:
                seen.add(key)

        if errors:
            # muestra un error general de formset (aparece arriba de la tabla)
            from django.forms import ValidationError
            raise ValidationError(errors)

# 👇 ESTE es el formset que debe usarse en la vista
CampoMedioPagoFormSet = inlineformset_factory(
    parent_model=TipoMedioPago,
    model=CampoMedioPago,
    form=CampoMedioPagoForm,
    formset=_BaseCampoMedioPagoFormSet,
    extra=0,             # 👈 importantísimo
    can_delete=True,     # 👈 para {{ f.DELETE }}
    fk_name="tipo",
)

# ---------------------------------
# Cliente: Form dinámico por "tipo"
# ---------------------------------
class MedioPagoClienteForm(forms.ModelForm):
    # Sobrescribimos 'tipo' para tener control total del widget y la UX
    tipo = forms.ModelChoiceField(
        queryset=TipoMedioPago.objects.filter(activo=True).exclude(engine='stripe').order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select w-full"}),
        help_text="Selecciona el tipo de medio de pago",
        required=True,
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

        # 1) Determinar el 'tipo' seleccionado
        tipo_obj = None

        # a) Si estoy editando y ya hay FK
        if getattr(self.instance, "pk", None) and getattr(self.instance, "tipo_id", None):
            tipo_obj = self.instance.tipo

        # b) Si viene por POST (form enviado) o por initial / querystring
        if tipo_obj is None:
            tipo_pk = self.data.get("tipo") or self.initial.get("tipo")
            print(f"DEBUG MedioPagoClienteForm: tipo_pk obtenido: {tipo_pk}") # Debugging
            if tipo_pk:
                try:
                    tipo_obj = TipoMedioPago.objects.get(pk=tipo_pk, activo=True)
                    print(f"DEBUG MedioPagoClienteForm: tipo_obj encontrado: {tipo_obj.nombre}") # Debugging
                except TipoMedioPago.DoesNotExist:
                    tipo_obj = None
                    print("DEBUG MedioPagoClienteForm: TipoMedioPago no encontrado o inactivo.") # Debugging

        # c) Fallback UX: si no hay selección y hay al menos un tipo activo, usamos el primero
        if tipo_obj is None:
            first_tipo = self.fields["tipo"].queryset.first()
            if first_tipo is not None:
                tipo_obj = first_tipo
                self.initial["tipo"] = first_tipo.pk
                print(f"DEBUG MedioPagoClienteForm: Usando primer tipo activo como fallback: {first_tipo.nombre}") # Debugging

        # 2) Construir campos dinámicos si tenemos tipo
        self._campos_config = []
        if tipo_obj:
            self.fields["tipo"].initial = tipo_obj.pk
            campos_qs = CampoMedioPago.objects.filter(tipo=tipo_obj, activo=True).order_by("nombre_campo")
            print(f"DEBUG MedioPagoClienteForm: Campos dinámicos para {tipo_obj.nombre}: {list(campos_qs)}") # Debugging
            for campo in campos_qs:
                nombre = campo.nombre_campo
                requerido = campo.obligatorio
                self.fields[nombre] = forms.CharField(
                    label=nombre,
                    required=requerido,
                    widget=forms.TextInput(attrs={"class": "form-input w-full"}),
                )
                if getattr(self.instance, "pk", None):
                    self.fields[nombre].initial = (self.instance.datos or {}).get(nombre, "")
                self._campos_config.append(campo)
        else:
            print("DEBUG MedioPagoClienteForm: No hay tipo_obj, no se construyen campos dinámicos.") # Debugging

    @property
    def campos_config(self):
        return getattr(self, "_campos_config", [])

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

            # Regex solo predefinida
            patron = campo.regex_opcional or ""
            if valor not in (None, "") and patron and not check_regex(patron, valor):
                errores[nombre] = "Formato inválido"

            datos[nombre] = valor

        if errores:
            raise forms.ValidationError(errores)

        self.instance.datos = datos
        return cleaned
