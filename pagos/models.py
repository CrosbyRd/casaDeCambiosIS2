"""
Módulo de modelos para la aplicación **Pagos**.

Contiene las definiciones de los modelos relacionados con los medios de pago
aceptados por los clientes, incluyendo la configuración de tipos, campos
personalizados, y validaciones dinámicas por cliente.

Modelos incluidos:
    - TipoMedioPago
    - CampoMedioPago
    - MedioPagoCliente
"""
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
    """
    Representa un **tipo de medio de pago** disponible en el sistema
    (por ejemplo: transferencia bancaria, tarjeta, billetera electrónica, etc.).

    Incluye la configuración de la comisión que aplica cada medio, el motor
    de procesamiento que utiliza (manual, SIPAP, Stripe, etc.) y metadatos.

    :param uuid id_tipo: Identificador único del tipo de medio de pago.
    :param str nombre: Nombre único que identifica el medio de pago.
    :param Decimal comision_porcentaje: Porcentaje de comisión aplicado (0–100).
    :param str descripcion: Descripción adicional o instrucciones.
    :param bool activo: Indica si el medio está disponible para uso.
    :param datetime creado_en: Fecha de creación del registro.
    :param datetime actualizado_en: Fecha de última actualización.
    :param str engine: Motor o integración usada para procesar pagos.
    :param dict engine_config: Configuración JSON específica del motor.
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)

    # Comisión en porcentaje que aplica este medio (0 a 100)
    comision_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Porcentaje de comisión que aplica este medio (0–100).",
    )

    # --- ### AÑADE ESTE BLOQUE DE CÓDIGO ### ---
    # Este es el campo que existe en tu BD pero falta en tu modelo
    bonificacion_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Porcentaje de bonificación que aplica este medio (0–100).",
    )
    # --- ### FIN DEL BLOQUE ### ---
    
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

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
    """
    Define un **campo dinámico** asociado a un tipo de medio de pago.

    Cada tipo puede tener múltiples campos requeridos (por ejemplo,
    número de cuenta, RUC, alias, email) con validaciones opcionales
    mediante expresiones regulares predefinidas.

    :param uuid id_campo: Identificador único del campo.
    :param TipoMedioPago tipo: Relación con el tipo de medio de pago.
    :param str nombre_campo: Nombre del campo visible o técnico.
    :param str tipo_dato: Tipo de dato (texto, número, teléfono, email, RUC).
    :param bool obligatorio: Indica si el campo es obligatorio.
    :param str regex_opcional: Patrón regex opcional de validación.
    :param bool activo: Define si el campo está activo.
    """

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

    id = models.AutoField(primary_key=True)
    tipo = models.ForeignKey(TipoMedioPago, related_name="campos", on_delete=models.CASCADE)
    nombre_campo = models.CharField(max_length=100)
    tipo_dato = models.CharField(max_length=15, choices=TipoDato.choices, default=TipoDato.TEXTO)
    obligatorio = models.BooleanField(default=False)

    # Solo regex predefinida
    regex_opcional = models.CharField(max_length=200, choices=RegexOpciones.choices, blank=True, default="")

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Campo de medio de pago"
        verbose_name_plural = "Campos de medios de pago"
        unique_together = ("tipo", "nombre_campo")

    def __str__(self):
        return f"{self.tipo.nombre} · {self.nombre_campo}"


# ----------------------------------------------------------------------------
# 3) MedioPagoCliente: instancia del cliente con datos dinámicos + predeterminado
# ----------------------------------------------------------------------------
class MedioPagoCliente(models.Model):
    """
    Representa un **medio de pago configurado por un cliente**.

    Contiene los datos específicos de ese cliente (guardados como JSON),
    y permite designar un medio predeterminado para operaciones futuras.

    :param uuid id_medio: Identificador único del medio de pago del cliente.
    :param Cliente cliente: Relación con el cliente propietario.
    :param TipoMedioPago tipo: Tipo de medio de pago utilizado.
    :param str alias: Nombre personalizado asignado por el cliente.
    :param dict datos: Información dinámica del medio (ej. número de cuenta).
    :param bool activo: Indica si el medio está activo.
    :param bool predeterminado: Indica si es el medio preferido por el cliente.
    :param datetime creado_en: Fecha de creación.
    :param datetime actualizado_en: Última modificación.
    """
    id = models.AutoField(primary_key=True)

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

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
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
        """
        Valida que los datos JSON del medio de pago cumplan con los
        campos activos y sus reglas de validación definidas.

        :raises ValidationError: Si faltan campos obligatorios, o si
                                 los valores no cumplen con el formato esperado.
        """
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
        """
        Guarda el medio de pago aplicando la lógica de consistencia:
        - Si se desactiva, se quita el estado de predeterminado.
        - Si se marca como predeterminado, desmarca los otros medios
          predeterminados del mismo cliente.
        """
        # Si se inactiva, también pierde el estado de predeterminado
        if not self.activo and self.predeterminado:
            self.predeterminado = False
        super().save(*args, **kwargs)
        # Si quedó como predeterminado, desmarcar otros del mismo cliente
        if self.predeterminado:
            MedioPagoCliente.objects.filter(
                cliente=self.cliente, predeterminado=True
            ).exclude(pk=self.pk).update(predeterminado=False)
