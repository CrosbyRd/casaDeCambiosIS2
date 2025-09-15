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
