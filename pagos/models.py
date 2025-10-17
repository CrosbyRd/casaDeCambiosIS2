import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

# ----------------------------------------------------------------------------
# 1) TipoMedioPago: define el tipo de método de pago + comisión %
# ----------------------------------------------------------------------------
class TipoMedioPago(models.Model):
    id_tipo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)

    # Comisión en porcentaje que aplica este medio (0 a 100)
    comision_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Porcentaje de comisión que aplica este medio (0–100).",
    )

    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True)

    ENGINE_CHOICES = [
        ('manual', 'Manual'),
        ('stripe', 'Stripe'),
        ('sipap', 'SIPAP'),
        ('local', 'Pasarela Local'), # Renombrado de 'simulador' a 'local'
    ]
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES, default='manual')
    engine_config = models.JSONField(default=dict, blank=True)
    
    def is_stripe(self) -> bool:
        return self.engine == 'stripe'

    class Meta:
        db_table = "pagos_tipo_medio"
        verbose_name = "Tipo de medio de pago"
        verbose_name_plural = "Tipos de medios de pago"
        permissions = [
            ("access_pagos_section", "Puede acceder a la sección de pagos"),
        ]

    def __str__(self):
        return self.nombre
    



# ----------------------------------------------------------------------------
# 2) CampoMedioPago: define los campos dinámicos por tipo
# ----------------------------------------------------------------------------
class CampoMedioPago(models.Model):
    class TipoDato(models.TextChoices):
        TEXTO = "texto", "Texto"
        NUMERO = "numero", "Número"
        TELEFONO = "telefono", "Teléfono"
        EMAIL = "email", "Email"
        RUC = "ruc", "RUC"

    class RegexOpciones(models.TextChoices):
        NINGUNO = "", "(sin regex)"
        SOLO_LETRAS   = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+$", "Solo letras" 
        SOLO_NUMEROS = r"^\d+$", "Solo números"
        EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$", "Email básico"
        TELEFONO_PY_LOCAL = r"^09\d{8}$", "Teléfono PY (09xxxxxxxx)"
        RUC_PY = r"^\d{6,8}-\d{1}$", "RUC PY (########-#)"

    id_campo = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.ForeignKey(TipoMedioPago, related_name="campos", on_delete=models.CASCADE)
    nombre_campo = models.CharField(max_length=100)
    tipo_dato = models.CharField(max_length=15, choices=TipoDato.choices, default=TipoDato.TEXTO)
    obligatorio = models.BooleanField(default=False)

    # Solo regex predefinida
    regex_opcional = models.CharField(max_length=200, choices=RegexOpciones.choices, blank=True, default="")

    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "pagos_campo_medio"
        verbose_name = "Campo de medio de pago"
        verbose_name_plural = "Campos de medios de pago"
        unique_together = ("tipo", "nombre_campo")

    def __str__(self):
        return f"{self.tipo.nombre} · {self.nombre_campo}"


# ----------------------------------------------------------------------------
# 3) MedioPagoCliente: instancia del cliente con datos dinámicos + predeterminado
# ----------------------------------------------------------------------------
class MedioPagoCliente(models.Model):
    id_medio = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 🔴 DUEÑO CORRECTO
    cliente = models.ForeignKey("clientes.Cliente",
                                related_name="medios_pago",
                                on_delete=models.CASCADE)

    tipo = models.ForeignKey(TipoMedioPago,
                             related_name="medios_cliente",
                             on_delete=models.PROTECT)

    alias = models.CharField(max_length=120, verbose_name="Proveedor")
    datos = models.JSONField(default=dict, blank=True)

    activo = models.BooleanField(default=True)
    predeterminado = models.BooleanField(default=False)

    creado_en = models.DateTimeField(default=timezone.now, editable=False)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pagos_medio_cliente"
        constraints = [
            # ✅ a lo sumo un predeterminado por CLIENTE
            models.UniqueConstraint(
                fields=["cliente"],
                condition=Q(predeterminado=True),
                name="uniq_medio_pago_predeterminado_por_cliente",
            ),
            # ✅ opcional: alias único por cliente+tipo
            models.UniqueConstraint(
                fields=["cliente", "tipo", "alias"],
                name="uniq_alias_por_cliente_y_tipo",
            ),
        ]

    def __str__(self):
        # Evitar RelatedObjectDoesNotExist en crear/instancias sin FK
        alias = self.alias or "—"
        try:
            tipo_nombre = self.tipo.nombre  # puede no existir aún
        except Exception:
            tipo_nombre = "—"
        estado = "(inactivo)" if getattr(self, "activo", True) is False else ""
        return f"{alias} · {tipo_nombre} {estado}".strip()

    # Validación: verificar que los datos cumplan con los campos activos del tipo
    def clean(self):
        errors = {}
        campos_activos = list(self.tipo.campos.filter(activo=True))
        datos = self.datos or {}

        import re

        # Mapeo de validadores ligeros por tipo de dato
        def _valida_tipo(nombre, valor, tipo):
            if valor in (None, ""):
                return None
            if tipo == CampoMedioPago.TipoDato.NUMERO:
                if not re.fullmatch(r"^-?\d+(?:[\.,]\d+)?$", str(valor)):
                    return f"{nombre}: debe ser numérico"
            elif tipo == CampoMedioPago.TipoDato.TELEFONO:
                if not re.fullmatch(r"^\+?\d{6,15}$", str(valor)):
                    return f"{nombre}: teléfono inválido"
            elif tipo == CampoMedioPago.TipoDato.EMAIL:
                if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(valor)):
                    return f"{nombre}: email inválido"
            elif tipo == CampoMedioPago.TipoDato.RUC:
                if not re.fullmatch(r"^\d{6,8}-\d{1}$", str(valor)):
                    return f"{nombre}: RUC inválido (########-#)"
            return None

        for campo in campos_activos:
            nombre = campo.nombre_campo
            valor = datos.get(nombre)
            if campo.obligatorio and (valor is None or str(valor).strip() == ""):
                errors[nombre] = "Es obligatorio"
                continue
            # Validación por tipo
            type_err = _valida_tipo(nombre, valor, campo.tipo_dato)
            if type_err:
                errors[nombre] = type_err
                continue
            # Validación por regex (solo la predefinida)
            patron = campo.regex_opcional or ""
            if patron and valor not in (None, ""):
                try:
                    if not re.fullmatch(patron, str(valor)):
                        errors[nombre] = "Formato inválido"
                except re.error:
                    errors[nombre] = "Regex inválida en configuración"

        if errors:
            raise ValidationError(errors)

    # Lógica de predeterminado y desactivación
    def save(self, *args, **kwargs):
        # Si se inactiva, también pierde el estado de predeterminado
        if not self.activo and self.predeterminado:
            self.predeterminado = False
        super().save(*args, **kwargs)
        # Si quedó como predeterminado, desmarcar otros del mismo cliente
        if self.predeterminado:
            MedioPagoCliente.objects.filter(
                cliente=self.cliente, predeterminado=True
            ).exclude(pk=self.pk).update(predeterminado=False)
