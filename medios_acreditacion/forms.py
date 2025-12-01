"""
Formularios de la aplicación **medios_acreditacion**.

.. module:: medios_acreditacion.forms
   :synopsis: Definición de formularios para la gestión de Tipos de Medio, Campos de Medio y Medios de clientes.

Este módulo implementa los formularios para:

- **TipoMedioForm**: formulario administrativo para crear y editar tipos de medio de acreditación.
- **CampoMedioForm**: formulario administrativo para configurar los campos de un tipo de medio.
- **MedioAcreditacionClienteForm**: formulario dinámico que construye campos en función del tipo de medio
  seleccionado por el cliente, con validaciones automáticas.
"""
from django import forms
from .models import TipoMedioAcreditacion, CampoMedioAcreditacion, MedioAcreditacionCliente
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
# -----------------------------
# Formulario para Tipos de medios (admin)
# -----------------------------
class TipoMedioForm(forms.ModelForm):
    """
    Formulario para la gestión de **Tipos de Medios de Acreditación** (administrador).

    **Modelo asociado**
    -------------------
    :class:`medios_acreditacion.models.TipoMedioAcreditacion`

    **Campos**
    ----------
    - ``nombre`` : nombre del tipo de medio.
    - ``descripcion`` : descripción opcional.
    - ``activo`` : checkbox para habilitar/deshabilitar.

    **Widgets personalizados**
    --------------------------
    - nombre → TextInput con clase *form-control*.
    - descripcion → Textarea con clase *form-control*.
    - activo → CheckboxInput con clase *form-check-input*.
    """
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
    """
    Formulario dinámico para la gestión de **Medios de Acreditación de Clientes**.

    Este formulario genera dinámicamente los campos en función del tipo de medio de
    acreditación seleccionado, aplicando validaciones específicas según el tipo de dato
    y expresiones regulares configuradas.

    **Modelo asociado**
    -------------------
    :class:`medios_acreditacion.models.MedioAcreditacionCliente`

    **Campos básicos**
    ------------------
    - ``tipo`` : tipo de medio de acreditación.
    - ``alias`` : alias personalizado del cliente.
    - ``activo`` : estado del medio.
    - ``predeterminado`` : indicador de si es el medio principal.

    **Métodos**
    -----------
    __init__(*args, **kwargs)
        Construye los campos dinámicos en base al tipo de medio seleccionado.
    clean() -> dict
        Valida y normaliza los datos dinámicos, aplicando validaciones específicas
        por tipo de dato y regex. Asigna el resultado al campo ``datos`` del modelo.
    """

    class Meta:
        model = CampoMedioAcreditacion
        fields = ["nombre", "tipo_dato", "obligatorio", "regex"]  # activo no es necesario para esta opción


# -----------------------------
# Formulario para Medios de clientes (dinámico)
# -----------------------------
# medios_acreditacion/forms.py
# medios_acreditacion/forms.py

class MedioAcreditacionClienteForm(forms.ModelForm):
    class Meta:
        model = MedioAcreditacionCliente
        fields = ("tipo", "alias", "activo", "predeterminado")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None) # Capturar el usuario si se pasa
        super().__init__(*args, **kwargs)

        tipo_obj = None
        raw_tipo = None

        # Intentar obtener el tipo de los datos enviados (POST) primero, considerando el prefijo
        if self.is_bound and self.prefix:
            raw_tipo = self.data.get(f"{self.prefix}-tipo")
        elif self.is_bound:
            raw_tipo = self.data.get("tipo")
        
        # Si no se encontró en self.data, intentar en initial
        if not raw_tipo:
            raw_tipo = self.initial.get("tipo") if isinstance(self.initial, dict) else None

        if isinstance(raw_tipo, TipoMedioAcreditacion):
            tipo_obj = raw_tipo
        elif raw_tipo:
            try:
                tipo_obj = TipoMedioAcreditacion.objects.get(pk=raw_tipo)
            except TipoMedioAcreditacion.DoesNotExist:
                tipo_obj = None

        if not tipo_obj and getattr(self.instance, "pk", None):
            if getattr(self.instance, "tipo_id", None):
                tipo_obj = self.instance.tipo

        if tipo_obj and not getattr(self.instance, "pk", None):
            self.instance.tipo = tipo_obj

        if not tipo_obj:
            return

        # ✅ Crear SIEMPRE como CharField
        for campo in tipo_obj.campos.filter(activo=True):
            field_name = f"campo_{campo.nombre}"
            self.fields[field_name] = forms.CharField(
                required=campo.obligatorio,
                label=campo.nombre,
            )

            # inicializar al editar
            if self.instance and self.instance.pk:
                valor_guardado = (self.instance.datos or {}).get(campo.nombre)
                if valor_guardado is not None:
                    self.initial[field_name] = valor_guardado

    def clean(self):
        """
        Valida los campos dinámicos en función de las reglas definidas
        en :class:`CampoMedioAcreditacion`.

        **Validaciones aplicadas**
        --------------------------
        - NUMERO → solo dígitos.
        - TELEFONO → dígitos, mínimo 9.
        - EMAIL → debe contener '@'.
        - RUC → formato ########-#.
        - Regex extra → validación personalizada.

        Retorna:
            dict: datos limpios y validados.
        """
        cleaned = super().clean()
        tipo = cleaned.get("tipo") or getattr(self.instance, "tipo", None)
        if not tipo:
            return cleaned

        datos = {}
        for campo in tipo.campos.filter(activo=True):
            field_name = f"campo_{campo.nombre}"
            valor = cleaned.get(field_name)

            if not valor:
                if campo.obligatorio:
                    self.add_error(field_name, "Este campo es obligatorio.")
                continue

            # ✅ Validaciones manuales seguras
            if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.NUMERO:
                if not valor.isdigit():
                    self.add_error(field_name, "Debe ser un número válido.")
            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.TELEFONO:
                if not valor.isdigit() or len(valor) < 9:
                    self.add_error(field_name, "Debe ser un teléfono válido (mín. 9 dígitos).")
            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.EMAIL:
                if "@" not in valor:
                    self.add_error(field_name, "Debe ser un correo electrónico válido.")
            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.RUC:
                import re
                if not re.match(r"^\d{6,8}-\d{1}$", valor):
                    self.add_error(field_name, "El RUC debe tener el formato ########-#")

            if campo.regex:
                import re
                if not re.match(campo.regex, valor):
                    self.add_error(field_name, "No cumple el formato requerido.")

            datos[campo.nombre] = valor

        self.instance.datos = datos
        return cleaned

class MedioAcreditacionClienteInOperacionForm(MedioAcreditacionClienteForm):
    """
    Formulario especializado para crear un MedioAcreditacionCliente desde la pasarela
    de `iniciar_operacion`. Hereda toda la lógica y campos del formulario base.
    Se personaliza para ocultar campos administrativos y preestablecer valores.
    """
    class Meta(MedioAcreditacionClienteForm.Meta):
        # Excluir 'activo' y 'predeterminado' ya que no deben ser manipulados por el usuario
        # en este contexto de creación rápida. Sus valores se establecerán programáticamente.
        exclude = ('activo', 'predeterminado',) 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que estos campos se preestablecen al crear la instancia
        if self.instance and not self.instance.pk: # Solo para nuevas instancias
            self.instance.activo = True
            self.instance.predeterminado = False
