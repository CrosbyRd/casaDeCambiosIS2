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
    """
    Form dinámico para que el cliente cargue los datos según el Tipo seleccionado.
    - Usamos nombres internos estables 'campo__<id_campo>' para los fields del form.
    - El label del field es el nombre legible del Campo.
    - En clean(), volcamos todo a instance.datos.
    """

    class Meta:
        model = MedioAcreditacionCliente
        fields = ["tipo", "alias", "activo"]   # 'datos' se maneja internamente
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "alias": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        # opcional: forzamos tipo desde la vista (crear?tipo=<uuid>)
        self.tipo_forzado = kwargs.pop("tipo_forzado", None)
        super().__init__(*args, **kwargs)

        # Descubrir el tipo:
        tipo = None

        # 1) En editar ya tenemos instance.tipo
        if getattr(self.instance, "pk", None):
            tipo = self.instance.tipo

        # 2) En crear POST: si el select 'tipo' viene en self.data
        if not tipo and "tipo" in self.data and self.data.get("tipo"):
            tipo = TipoMedioAcreditacion.objects.filter(pk=self.data.get("tipo")).first()

        # 3) En crear GET con ?tipo=<uuid> (pasado como 'tipo_forzado' desde la vista)
        if not tipo and self.tipo_forzado:
            tipo = self.tipo_forzado

        # 4) Último intento: initial
        if not tipo:
            tipo = self.initial.get("tipo")

        self._campos_def = []  # (nombre_interno, campo_model) para usar luego en clean()

        if tipo:
            # Solo campos activos
            for campo in tipo.campos.filter(activo=True).order_by("nombre"):
                name = f"campo__{campo.id_campo}"   # nombre interno estable
                self._campos_def.append((name, campo))

                # construir el Field en función del tipo_dato
                if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.NUMERO:
                    field = forms.IntegerField(required=campo.obligatorio, label=campo.nombre)
                elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.TELEFONO:
                    field = forms.CharField(required=campo.obligatorio, label=campo.nombre, min_length=9, max_length=15)
                elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.EMAIL:
                    field = forms.EmailField(required=campo.obligatorio, label=campo.nombre)
                elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.RUC:
                    field = forms.RegexField(regex=r"^\d{6,8}-\d{1}$",
                                             required=campo.obligatorio,
                                             label=campo.nombre,
                                             error_messages={"invalid": "El RUC debe tener el formato ########-#"})
                else:  # TEXTO
                    field = forms.CharField(required=campo.obligatorio, label=campo.nombre)

                # Validación extra (regex) si existe
                if campo.regex:
                    field.validators.append(forms.RegexField(regex=campo.regex).validators[0])

                self.fields[name] = field

                # Si estamos editando, precargar el valor desde instance.datos
                if getattr(self.instance, "pk", None):
                    # Intentar por nombre (lo más natural en tu modelo actual)
                    valor = (self.instance.datos or {}).get(campo.nombre)
                    # (si el día de mañana cambian nombres, acá podrías buscar también por id_campo)
                    if valor not in (None, ""):
                        self.initial[name] = valor

        # Si el tipo viene “forzado” desde la vista, bloquea el select (solo UX)
        if self.tipo_forzado:
            self.fields["tipo"].initial = self.tipo_forzado.pk
            self.fields["tipo"].widget.attrs["readonly"] = True
            self.fields["tipo"].widget.attrs["disabled"] = True

    def clean(self):
        cleaned = super().clean()

        # Qué tipo vamos a validar
        tipo = getattr(self.instance, "tipo", None) or cleaned.get("tipo") or self.tipo_forzado
        if not tipo:
            return cleaned  # sin tipo no hay campos dinámicos

        datos = {}
        for name, campo in self._campos_def:
            valor = cleaned.get(name)

            # Obligatoriedad (por si acaso)
            if campo.obligatorio and (valor in (None, "", [])):
                self.add_error(name, "Este campo es obligatorio.")
                continue

            # Guardar (si vino algo o si no es obligatorio)
            if valor is not None:
                datos[campo.nombre] = valor

        # Guardar todo en la instancia; el ModelForm guardará el modelo completo después
        self.instance.datos = datos

        return cleaned
