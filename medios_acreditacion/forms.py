from django import forms
from django.core.exceptions import ValidationError
from .models import TipoMedioAcreditacion, CampoMedioAcreditacion, MedioAcreditacionCliente


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
class MedioAcreditacionClienteForm(forms.ModelForm):
    """
    Este form construye dinámicamente los campos según el tipo de medio elegido.
    Los campos definidos por el admin en CampoMedioAcreditacion se transforman en inputs reales.
    """

    class Meta:
        model = MedioAcreditacionCliente
        fields = ["tipo", "activo"]  # "datos" se maneja aparte
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si ya tenemos un tipo seleccionado, agregamos dinámicamente los campos
        tipo = self.instance.tipo if self.instance.pk else self.initial.get("tipo")

        if tipo:
            campos = tipo.campos.all()
            for campo in campos:
                field_name = f"campo_{campo.nombre}"

                if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.NUMERO:
                    field = forms.IntegerField(required=campo.obligatorio, label=campo.nombre)

                elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.TELEFONO:
                    field = forms.CharField(
                        required=campo.obligatorio,
                        label=campo.nombre,
                        min_length=9,
                        max_length=15
                    )

                elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.EMAIL:
                    field = forms.EmailField(required=campo.obligatorio, label=campo.nombre)

                elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.RUC:
                    field = forms.RegexField(
                        regex=r"^\d{6,8}-\d{1}$",
                        required=campo.obligatorio,
                        label=campo.nombre,
                        error_messages={"invalid": "El RUC debe tener el formato ########-#"}
                    )

                else:  # TEXTO
                    field = forms.CharField(required=campo.obligatorio, label=campo.nombre)

                # Aplicar regex custom si está definido
                if campo.regex:
                    field.validators.append(forms.RegexField(regex=campo.regex).validators[0])

                self.fields[field_name] = field

    def clean(self):
        """Guarda los datos dinámicos en el campo JSON 'datos'"""
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")

        if tipo:
            datos = {}
            for campo in tipo.campos.all():
                field_name = f"campo_{campo.nombre}"
                valor = cleaned_data.get(field_name)
                if valor is not None:
                    datos[campo.nombre] = valor
            self.instance.datos = datos

        return cleaned_data
