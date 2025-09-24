import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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
    datos = models.JSONField(default=dict, verbose_name=_("Datos del medio"))
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def clean(self):
        """Valida que los datos cargados coincidan con lo definido por el admin"""
        errores = {}
        # ✅ ahora solo validamos campos activos
        for campo in self.tipo.campos.filter(activo=True):
            valor = self.datos.get(campo.nombre)

            if campo.obligatorio and not valor:
                errores[campo.nombre] = _("Este campo es obligatorio.")
                continue

            if valor:
                if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.NUMERO and not str(valor).isdigit():
                    errores[campo.nombre] = _("Debe ser un número válido.")

                if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.TELEFONO:
                    if not str(valor).isdigit() or len(str(valor)) < 9:
                        errores[campo.nombre] = _("Debe ser un teléfono válido (mín. 9 dígitos).")

                if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.EMAIL and "@" not in valor:
                    errores[campo.nombre] = _("Debe ser un correo electrónico válido.")

                if campo.tipo_dato == CampoMedioAcreditacion.TipoDato.RUC:
                    import re
                    if not re.match(r"^\d{6,8}-\d{1}$", valor):
                        errores[campo.nombre] = _("El RUC debe tener el formato ########-#.")

                if campo.regex:
                    import re
                    if not re.match(campo.regex, str(valor)):
                        errores[campo.nombre] = _("No cumple el formato requerido.")

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.tipo.nombre} - {self.cliente.nombre}"
