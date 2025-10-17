# monedas/models.py
"""
Módulo de modelos de la aplicación **monedas**.

.. module:: monedas.models
   :synopsis: Catálogo de monedas y metadatos asociados.

Este módulo define el modelo :class:`Moneda`, utilizado como catálogo
centralizado de monedas con las que opera el sistema. Incluye metadatos
operativos (p. ej., decimales, mínima denominación) y un permiso de acceso
a la sección de administración de monedas.
"""

from django.db import models
from django.conf import settings


class Moneda(models.Model):
    """
    Representa una **moneda** del sistema.

    Se utiliza como catálogo de monedas que pueden participar en operaciones
    (cotizaciones, calculadora, etc.). Además, define un permiso de acceso a
    la sección de administración de monedas.

    **Atributos**
    -------------
    codigo : :class:`django.db.models.CharField`
        Código de la moneda (p. ej. ``USD``, ``EUR``, ``PYG``). Debe ser único.
    nombre : :class:`django.db.models.CharField`
        Nombre legible de la moneda (p. ej. *Dólar estadounidense*).
    simbolo : :class:`django.db.models.CharField`
        Símbolo de la moneda (p. ej. ``$``, ``€``, ``₲``).
    fecha_creacion : :class:`django.db.models.DateTimeField`
        Fecha/hora de creación del registro. Se asigna automáticamente.
    decimales : :class:`django.db.models.PositiveSmallIntegerField`
        Cantidad de decimales con los que se representa la moneda.
        Útil para formateo y validaciones. Valor por defecto: ``2``.
    minima_denominacion : :class:`django.db.models.PositiveIntegerField`
        Mínima unidad operable (p. ej., ``1`` para monedas enteras, ``5`` si
        solo se opera en múltiplos de 5). Valor por defecto: ``1``.
    ultima_actualizacion_tasa : :class:`django.db.models.DateTimeField`
        Marca temporal de la última actualización de tasa/cotización conocida.
        Puede ser nula si nunca se actualizó.
    admite_en_linea : :class:`django.db.models.BooleanField`
        Indica si la moneda está habilitada para operaciones **en línea**.
    admite_terminal : :class:`django.db.models.BooleanField`
        Indica si la moneda está habilitada para operaciones en **terminal**.

    .. note::
       El permiso personalizado ``monedas.access_monedas_section`` permite
       controlar el acceso a las vistas de administración/listado de monedas.
    """

    codigo = models.CharField(
        max_length=5,
        unique=True,
        help_text="Código ISO/corto de la moneda (p. ej. USD, EUR, PYG). Debe ser único."
    )
    nombre = models.CharField(
        max_length=50,
        help_text="Nombre legible de la moneda (p. ej. Dólar estadounidense)."
    )
    simbolo = models.CharField(
        max_length=5,
        help_text="Símbolo de la moneda (p. ej. $, €, ₲)."
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación del registro (asignado automáticamente)."
    )

    # Requerimientos ERS
    decimales = models.PositiveSmallIntegerField(
        default=2,
        help_text="Cantidad de decimales con los que se representa la moneda (por defecto: 2)."
    )
    minima_denominacion = models.PositiveIntegerField(
        default=1,
        help_text="Mínima denominación operable (p. ej., 1, 5, 10)."
    )
    ultima_actualizacion_tasa = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última fecha/hora en la que se actualizó la tasa/cotización. Puede ser nulo."
    )

    admite_en_linea = models.BooleanField(
        default=True,
        help_text="Si está activo, la moneda puede usarse en operaciones en línea."
    )
    admite_terminal = models.BooleanField(
        default=True,
        help_text="Si está activo, la moneda puede usarse en operaciones de terminal."
    )

    class Meta:
        """
        Metadatos del modelo :class:`Moneda`.

        Define un permiso específico para restringir el acceso a la sección de
        administración de monedas.

        **Permisos**
        ------------
        - ``access_monedas_section``: *Puede acceder a la sección de Monedas*.
        """
        permissions = [
            ("access_monedas_section", "Puede acceder a la sección de Monedas"),
        ]

    def __str__(self) -> str:
        """
        Representación legible de la moneda.

        :return: Cadena con el formato ``\"{nombre} ({codigo})\"``.
        :rtype: str
        """
        return f"{self.nombre} ({self.codigo})"


# ==============================
# Inventario TED (en app monedas)
# ==============================

class TedDenominacion(models.Model):
    """
    Denominaciones manejadas por el TED para una moneda dada.

    ``valor`` se almacena como entero en la unidad de la moneda (p. ej. 1, 2, 5, 10, 20, 50, 100).
    """
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name="denominaciones_ted",
        help_text="Moneda a la que pertenece la denominación."
    )
    valor = models.PositiveIntegerField(
        help_text="Valor facial (entero) de la denominación. Ej.: 1, 2, 5, 10, 20, 50, 100."
    )
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = (("moneda", "valor"),)
        ordering = ["moneda__codigo", "valor"]
        permissions = [
            ("access_ted_inventory", "Puede gestionar el inventario del TED"),
        ]

    def __str__(self) -> str:
        return f"{self.moneda.codigo} {self.valor}"


class TedInventario(models.Model):
    """
    Stock disponible por denominación **y ubicación** para la terminal TED.

    .. important::
       Desde esta versión, el inventario se particiona por ``ubicacion``. Esto
       permite tener múltiples terminales (o sucursales) con stock independiente.

    **Restricción de unicidad**
    ---------------------------
    Se garantiza un único registro por combinación ``(denominacion, ubicacion)``.

    **Compatibilidad**
    ------------------
    El ``related_name`` de la relación inversa se mantiene en ``stock`` para
    conservar compatibilidad con código existente, pero ahora referirá a un
    *manager* (conjunto de stocks) en lugar de una única instancia.
    """
    denominacion = models.ForeignKey(
        TedDenominacion,
        on_delete=models.PROTECT,
        related_name="stock",  # se mantiene el nombre histórico
        help_text="Denominación cuyo stock se registra."
    )
    ubicacion = models.CharField(
        max_length=180,
        help_text="Ubicación física/lógica del TED (ej.: 'Campus, San Lorenzo – Paraguay')."
    )
    cantidad = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["denominacion__moneda__codigo", "denominacion__valor", "ubicacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["denominacion", "ubicacion"],
                name="uniq_tedinventario_den_ubicacion",
            ),
        ]
        indexes = [
            models.Index(fields=["ubicacion"], name="idx_tedinv_ubicacion"),
        ]

    def __str__(self) -> str:
        return f"Stock {self.denominacion} @ {self.ubicacion} = {self.cantidad}"


class TedMovimiento(models.Model):
    """
    Movimiento de inventario TED (histórico).

    ``delta`` > 0 incrementa stock; ``delta`` < 0 descuenta stock.
    """
    MOTIVO_AJUSTE = "AJUSTE"
    MOTIVO_COMPRA = "COMPRA"  # Cliente compra USD/EUR → retiro billetes
    MOTIVO_VENTA = "VENTA"    # Cliente vende USD/EUR → depósito billetes
    MOTIVO_CHEQUE = "CHEQUE"  # Depósito de cheque (mock)
    MOTIVO_OTRO = "OTRO"

    MOTIVO_CHOICES = [
        (MOTIVO_AJUSTE, "Ajuste manual"),
        (MOTIVO_COMPRA, "Compra cliente (retiro billetes)"),
        (MOTIVO_VENTA, "Venta cliente (depósito billetes)"),
        (MOTIVO_CHEQUE, "Depósito de cheque (mock)"),
        (MOTIVO_OTRO, "Otro"),
    ]

    denominacion = models.ForeignKey(
        TedDenominacion,
        on_delete=models.PROTECT,
        related_name="movimientos"
    )
    delta = models.IntegerField(help_text="Variación de stock. Positivo suma, negativo resta.")
    motivo = models.CharField(max_length=12, choices=MOTIVO_CHOICES, default=MOTIVO_OTRO)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movimientos_ted"
    )
    # Referencia opcional a transacción (placeholder mientras el módulo está en mock)
    transaccion_ref = models.CharField(
        max_length=64,
        blank=True,
        help_text="Referencia textual/ID externo de la transacción (opcional)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        signo = "+" if self.delta >= 0 else "-"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.denominacion} {signo}{abs(self.delta)} ({self.motivo})"
