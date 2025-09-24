from django import forms
from .models import TipoMedioAcreditacion, CampoMedioAcreditacion, MedioAcreditacionCliente
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
# -----------------------------
# Formulario para Tipos de medios (admin)
# -----------------------------
class TipoMedioForm(forms.ModelForm):
    class Meta:
        model = TipoMedioAcreditacion
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


# -----------------------------
# Formulario para Campos de medios (admin)
class CampoMedioForm(forms.ModelForm):
    class Meta:
        model = CampoMedioAcreditacion
        fields = ["nombre", "tipo_dato", "obligatorio", "regex"]  # activo no es necesario para esta opción


# -----------------------------
# Formulario para Medios de clientes (dinámico)
# -----------------------------
# medios_acreditacion/forms.py

class MedioAcreditacionClienteForm(forms.ModelForm):
    class Meta:
        model = MedioAcreditacionCliente
        fields = ("tipo", "alias", "activo")  # más los dinámicos…

    def __init__(self, *args, **kwargs):
        # No necesitamos 'user' aquí
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 1) Intentar tomar el tipo del POST o del initial (?tipo=…)
        tipo_obj = None
        raw_tipo = self.data.get("tipo") or (
            self.initial.get("tipo") if isinstance(self.initial, dict) else None
        )

        if isinstance(raw_tipo, TipoMedioAcreditacion):
            tipo_obj = raw_tipo
        elif raw_tipo:
            try:
                tipo_obj = TipoMedioAcreditacion.objects.get(pk=raw_tipo)
            except TipoMedioAcreditacion.DoesNotExist:
                tipo_obj = None

        # 2) Si no vino de POST/initial y estamos EDITANDO, usar tipo_id
        if not tipo_obj and getattr(self.instance, "pk", None):
            # Esta línea es SEGURA: no usa el descriptor, solo el FK crudo
            if getattr(self.instance, "tipo_id", None):
                # Ahora sí es seguro resolver el objeto
                tipo_obj = self.instance.tipo

        # 3) En crear, si ya resolví tipo, lo coloco en la instancia
        if tipo_obj and not getattr(self.instance, "pk", None):
            self.instance.tipo = tipo_obj

        # 4) Si todavía no hay tipo, no creo campos dinámicos (se crearán
        #    cuando el usuario seleccione uno y se envíe el POST)
        if not tipo_obj:
            return

        # === A partir de aquí, tu lógica actual de campos dinámicos ===
        # Por ejemplo:
        for campo in tipo_obj.campos.filter(activo=True):
            field_name = f"campo_{campo.nombre}"

            if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.NUMERO:
                field = forms.IntegerField(required=campo.obligatorio, label=campo.nombre)
            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.TELEFONO:
                field = forms.CharField(
                    required=campo.obligatorio, label=campo.nombre, min_length=9, max_length=15
                )
            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.EMAIL:
                field = forms.EmailField(required=campo.obligatorio, label=campo.nombre)
            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.RUC:
                field = forms.RegexField(
                    regex=r"^\d{6,8}-\d{1}$",
                    required=campo.obligatorio,
                    label=campo.nombre,
                    error_messages={"invalid": "El RUC debe tener el formato ########-#"},
                )
            else:
                field = forms.CharField(required=campo.obligatorio, label=campo.nombre)

            if campo.regex:
                field.validators.append(
                    forms.RegexField(regex=campo.regex).validators[0]
                )

            self.fields[field_name] = field

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo") or getattr(self.instance, "tipo", None)
        if not tipo:
            # sin tipo no empaquetamos datos dinámicos
            return cleaned

        datos = {}
        for campo in tipo.campos.filter(activo=True):
            valor = cleaned.get(f"campo_{campo.nombre}", None)
            if valor is not None:
                datos[campo.nombre] = valor
        self.instance.datos = datos
        return cleaned
