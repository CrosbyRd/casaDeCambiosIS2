"""
Modelos de la aplicación **medios_acreditacion**.

.. module:: medios_acreditacion.models
   :synopsis: Definición de modelos para tipos de medios de acreditación, sus campos y la relación con clientes.

Este módulo implementa los modelos que representan:

- **TipoMedioAcreditacion**: categoría o clase de medio de acreditación (ej. tarjeta, cuenta bancaria).
- **CampoMedioAcreditacion**: campos dinámicos configurables por cada tipo (ej. número, alias, email).
- **MedioAcreditacionCliente**: instancia concreta de un medio asociado a un cliente, con validaciones,
  alias, y posibilidad de marcar uno como predeterminado.

Incluye validaciones personalizadas, restricciones únicas condicionales y lógica para manejo de estados
(activo/inactivo, predeterminado).
"""
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import re
from django.core.exceptions import ValidationError
from django.db.models import Q, UniqueConstraint

class TipoMedioAcreditacion(models.Model):
    """
    Modelo que representa un **tipo de medio de acreditación**.

    Ejemplos: "Tarjeta de crédito", "Cuenta bancaria", "Billetera virtual".

    **Campos**
    ----------
    id_tipo : UUIDField
        Identificador único del tipo (clave primaria).
    nombre : CharField
        Nombre del tipo (único).
    descripcion : TextField
        Descripción opcional.
    activo : BooleanField
        Indica si el tipo está habilitado.

    **Meta**
    --------
    - Permisos personalizados:
      - ``access_medios_acreditacion`` → acceso a la sección administrativa.

    **Métodos**
    -----------
    __str__() -> str
        Retorna el nombre del tipo.
    """
    id_tipo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre"))
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)


    class Meta:
        permissions = [
            # 👉 Permiso “de acceso” para la sección admin de Tipos/ Campos
            ("access_medios_acreditacion", "Puede gestionar métodos de pago (Tipos de Medio y Campos)"),
        ]

    def __str__(self):
        return self.nombre


class CampoMedioAcreditacion(models.Model):
    """
    Modelo que define los **campos configurables** para un tipo de medio de acreditación.

    Ejemplo: para "Tarjeta de crédito" se podrían definir los campos "Número" (número),
    "Titular" (texto), "Fecha vencimiento" (texto).

    **Enums internos**
    ------------------
    - TipoDato: tipos de datos soportados (texto, número, teléfono, email, RUC).
    - RegexOpciones: expresiones regulares predefinidas para validaciones adicionales.

    **Campos**
    ----------
    id_campo : UUIDField
        Identificador único del campo.
    tipo_medio : ForeignKey
        Relación con :class:`TipoMedioAcreditacion`.
    nombre : CharField
        Nombre del campo (ej. "Número de tarjeta").
    tipo_dato : CharField
        Tipo de dato (controlado por TipoDato).
    obligatorio : BooleanField
        Si el campo es requerido.
    regex : CharField
        Expresión regular opcional para validación extra.
    activo : BooleanField
        Estado activo/inactivo.

    **Métodos**
    -----------
    __str__() -> str
        Retorna el nombre, tipo y estado del campo.
    """
    class TipoDato(models.TextChoices):
        TEXTO = "texto", _("Texto")
        NUMERO = "numero", _("Número")
        TELEFONO = "telefono", _("Teléfono")
        EMAIL = "email", _("Email")
        RUC = "ruc", _("RUC")

    class RegexOpciones(models.TextChoices):
        NINGUNO = "", _("Sin validación extra")
        SOLO_NUMEROS = r"^[0-9]+$", _("Solo números")
        SOLO_LETRAS = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$", _("Solo letras")
        EMAIL = r"^[^@]+@[^@]+\.[^@]+$", _("Correo electrónico válido")
        TELEFONO = r"^\d{9,15}$", _("Teléfono (9 a 15 dígitos)")
        RUC = r"^\d{6,8}-\d{1}$", _("RUC (########-#)")


    id_campo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_medio = models.ForeignKey(
        TipoMedioAcreditacion, on_delete=models.CASCADE, related_name="campos"
    )
    nombre = models.CharField(max_length=50, verbose_name=_("Nombre del campo"))
    tipo_dato = models.CharField(max_length=20, choices=TipoDato.choices, default=TipoDato.TEXTO)
    obligatorio = models.BooleanField(default=True)
    regex = models.CharField(
        max_length=200,
        choices=RegexOpciones.choices,
        blank=True,
        null=True,
        verbose_name=_("Validación extra"),
        help_text=_("Regla de validación que se aplicará automáticamente")
    )
    activo = models.BooleanField(default=True)  # 👈 ahora cada campo puede desactivarse

    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"{self.nombre} ({self.tipo_dato}) - {estado}"


class MedioAcreditacionCliente(models.Model):
    """
    Modelo que representa un **medio de acreditación asociado a un cliente**.

    Contiene la información concreta de un cliente para un tipo de medio
    (ej. tarjeta, cuenta, billetera), con campos dinámicos validados según
    el tipo.

    **Campos**
    ----------
    id_medio : UUIDField
        Identificador único del medio.
    cliente : ForeignKey
        Relación con el modelo ``clientes.Cliente``.
    tipo : ForeignKey
        Tipo de medio (relación con :class:`TipoMedioAcreditacion`).
    alias : CharField
        Alias personalizado del cliente (ej. "Mi Visa personal").
    datos : JSONField
        Diccionario con pares campo-valor según lo definido en el tipo.
    activo : BooleanField
        Estado activo/inactivo del medio.
    creado_en : DateTimeField
        Fecha de creación.
    actualizado_en : DateTimeField
        Fecha de última modificación.
    predeterminado : BooleanField
        Marca si es el medio principal del cliente.

    **Meta**
    --------
    - Restricción única condicional: solo un medio predeterminado por cliente.

    **Métodos**
    -----------
    __str__() -> str
        Retorna una representación "<tipo> - <cliente>".
    clean() -> None
        Valida que los datos coincidan con los campos definidos por el tipo.
    save(*args, **kwargs) -> None
        Garantiza unicidad del predeterminado y desactiva si corresponde.
    """
    id_medio = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="medios_acreditacion"
    )
    tipo = models.ForeignKey(
        TipoMedioAcreditacion,
        on_delete=models.PROTECT,
        related_name="medios_cliente"
    )

    # 👇 nuevo campo
    alias = models.CharField(max_length=100, blank=True, default="")

    datos = models.JSONField(default=dict, verbose_name=_("Datos del medio"))
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    predeterminado = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["cliente"],
                condition=Q(predeterminado=True),
                name="uniq_default_medio_por_cliente",
            ),
        ]


    def __str__(self):
        # ← evita disparar el descriptor de FK cuando todavía no hay tipo/cliente
        t = self.tipo.nombre if getattr(self, "tipo_id", None) else "—"
        c = self.cliente.nombre if getattr(self, "cliente_id", None) else "—"
        return f"{t} - {c}"


    def clean(self):
        """Valida que los datos cargados coincidan con lo definido por el admin."""
        if not self.tipo_id:
            return

        errores = {}
        datos = self.datos or {}

        for campo in self.tipo.campos.filter(activo=True):
            key_form = f"campo_{campo.nombre}"   # <-- nombre que SÍ existe en el form
            valor = datos.get(campo.nombre)

            # Obligatorio
            if campo.obligatorio and (valor is None or str(valor).strip() == ""):
                errores[key_form] = _("Este campo es obligatorio.")
                continue

            if valor is None or str(valor).strip() == "":
                continue  # opcional vacío, nada más que validar

            svalor = str(valor)

            # Validaciones por tipo
            if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.NUMERO:
                if not svalor.isdigit():
                    errores[key_form] = _("Debe ser un número válido.")

            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.TELEFONO:
                if not svalor.isdigit() or len(svalor) < 9 or len(svalor) > 15:
                    errores[key_form] = _("Debe ser un teléfono válido (9 a 15 dígitos).")

            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.EMAIL:
                if "@" not in svalor or "." not in svalor.rsplit("@", 1)[-1]:
                    errores[key_form] = _("Debe ser un correo electrónico válido.")

            elif campo.tipo_dato == CampoMedioAcreditacion.TipoDato.RUC:
                if not re.match(r"^\d{6,8}-\d{1}$", svalor):
                    errores[key_form] = _("El RUC debe tener el formato ########-#.")

            # Regex extra (si el admin lo definió)
            if campo.regex:
                if not re.match(campo.regex, svalor):
                    errores[key_form] = _("No cumple el formato requerido.")

            # 👇 reglas del predeterminado
        if self.predeterminado and not self.activo:
            errores["predeterminado"] = _("No puede ser predeterminado si está inactivo.")

        if errores:
            # 👈 devolvemos dict con keys que existen en el form → no explota
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
            # Si marco este como predeterminado, desmarco los demás del mismo cliente
            if self.predeterminado and self.cliente_id:
                MedioAcreditacionCliente.objects.filter(
                    cliente_id=self.cliente_id,
                    predeterminado=True
                ).exclude(pk=self.pk).update(predeterminado=False)

            # Si se desactiva, no puede quedar como predeterminado
            if not self.activo and self.predeterminado:
                self.predeterminado = False

            return super().save(*args, **kwargs)
        



