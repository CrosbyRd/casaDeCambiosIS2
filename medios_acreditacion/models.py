import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import re
from django.core.exceptions import ValidationError


class TipoMedioAcreditacion(models.Model):
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

        if errores:
            # 👈 devolvemos dict con keys que existen en el form → no explota
            raise ValidationError(errores)

        



