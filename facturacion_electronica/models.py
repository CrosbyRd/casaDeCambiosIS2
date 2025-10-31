"""
Modelos de la app Facturación Electrónica.

.. module:: facturacion_electronica.models
   :synopsis: Modelos propios del módulo de Facturación Electrónica.

Incluye:
- :class:`EmisorFacturaElectronica`: Representa la información de un emisor de facturas electrónicas.
- :class:`DocumentoElectronico`: Representa una factura o nota de crédito electrónica generada.
- :class:`ItemDocumentoElectronico`: Representa un ítem dentro de un Documento Electrónico.
"""
from django.db import models
from django.conf import settings
import uuid
from django.contrib.postgres.fields import JSONField  # Para almacenar JSON de la API
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils import timezone

class EmisorFacturaElectronica(models.Model):
    """
    Representa la información de un emisor de facturas electrónicas.

    Este modelo almacena todos los datos necesarios para identificar a un emisor
    ante el sistema de facturación electrónica, incluyendo su RUC, dirección,
    numeración de timbrado y rangos de facturación.

    :param nombre: Razón social o nombre del emisor.
    :param ruc: Número de Identificación Tributaria (RUC) del emisor (sin DV).
    :param dv_ruc: Dígito Verificador del RUC.
    :param email_emisor: Email de contacto del emisor.
    :param telefono: Teléfono de contacto del emisor.
    :param codigo_departamento: Código del departamento de la dirección del emisor.
    :param descripcion_departamento: Descripción del departamento.
    :param codigo_ciudad: Código de la ciudad de la dirección del emisor.
    :param descripcion_ciudad: Descripción de la ciudad.
    :param direccion: Dirección física del emisor.
    :param numero_casa: Número de casa de la dirección.
    :param pais: Código de país (por defecto "PY").
    :param establecimiento: Número de establecimiento (3 dígitos).
    :param punto_expedicion: Número de punto de expedición (3 dígitos).
    :param numero_timbrado_actual: Número de timbrado actual (8 dígitos).
    :param fecha_inicio_timbrado: Fecha de inicio de vigencia del timbrado.
    :param auth_token: Token de autenticación para la API de FacturaSegura.
    :param token_generado_at: Fecha y hora de generación del token.
    :param activo: Indica si el emisor está activo en el sistema.
    :param rango_numeracion_inicio: Número inicial del rango de numeración de facturas.
    :param rango_numeracion_fin: Número final del rango de numeración de facturas.
    :param siguiente_numero_factura: Próximo número de factura a emitir.
    """
    # Identificación del emisor (coincidir con XML)
    nombre = models.CharField(max_length=255, verbose_name="Razón social / Nombre")
    ruc = models.CharField(
        max_length=8,
        validators=[RegexValidator(r'^\d{7,8}$')],
        verbose_name="RUC (sin DV)"
    )
    dv_ruc = models.CharField(
        max_length=1,
        validators=[RegexValidator(r'^\d$')],
        verbose_name="DV"
    )

    # Datos de contacto
    email_emisor= models.EmailField(blank=True, null=True, verbose_name="Email de contacto")
    telefono = models.CharField(max_length=25, blank=True, null=True, verbose_name="Teléfono de contacto")

    # Dirección (coincidente con nodos de cDepEmi, dDesDepEmi, cCiuEmi, dDesCiuEmi, dDirEmi, dNumCas, cPaisEmi)
    codigo_departamento = models.PositiveIntegerField(blank=True, null=True, verbose_name="Código Dpto (cDepEmi)")
    descripcion_departamento = models.CharField(max_length=60, blank=True, null=True, verbose_name="Desc. Dpto (dDesDepEmi)")
    codigo_ciudad = models.PositiveIntegerField(blank=True, null=True, verbose_name="Código Ciudad (cCiuEmi)")
    descripcion_ciudad = models.CharField(max_length=60, blank=True, null=True, verbose_name="Desc. Ciudad (dDesCiuEmi)")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección (dDirEmi)")
    numero_casa = models.CharField(max_length=10, blank=True, null=True, verbose_name="N° Casa (dNumCas)")
    pais = models.CharField(max_length=2, default="PY", verbose_name="País (cPaisEmi)")

    # Numeración fija del ejercicio (establecimiento y punto)
    establecimiento = models.CharField(
        max_length=3,
        validators=[RegexValidator(r'^\d{3}$')],
        verbose_name="Establecimiento (3 dígitos, ej. 001)"
    )
    punto_expedicion = models.CharField(
        max_length=3,
        validators=[RegexValidator(r'^\d{3}$')],
        verbose_name="Punto de expedición (3 dígitos, ej. 003)"
    )

    # Timbrado (según XML del profe: dNumTim y dFeIniT)
    numero_timbrado_actual = models.CharField(
        max_length=8,
        validators=[RegexValidator(r'^\d{8}$')],
        verbose_name="Número de Timbrado (8 dígitos, ej. 02595733)"
    )
    fecha_inicio_timbrado = models.DateField(
        verbose_name="Fecha de inicio de Timbrado (YYYY-MM-DD)"
    )


    auth_token = models.TextField(blank=True, null=True, verbose_name="Token de autenticación (FacturaSegura)")
    token_generado_at = models.DateTimeField(blank=True, null=True, verbose_name="Fecha/hora de generación del token")

    # Estado del emisor en el sistema
    activo = models.BooleanField(default=True, verbose_name="Emisor activo")

    # --- NUEVOS CAMPOS (numeración 401–450) ---
    rango_numeracion_inicio = models.PositiveIntegerField(default=401, verbose_name="Inicio de numeración")
    rango_numeracion_fin = models.PositiveIntegerField(default=450, verbose_name="Fin de numeración")
    siguiente_numero_factura = models.PositiveIntegerField(default=401, verbose_name="Próximo número a emitir")


    class Meta:
        verbose_name = "Emisor de Factura Electrónica"
        verbose_name_plural = "Emisores de Factura Electrónica"
        constraints = [
            models.UniqueConstraint(
                fields=["ruc", "dv_ruc", "establecimiento", "punto_expedicion", "numero_timbrado_actual"],
                name="uniq_emisor_ruc_estab_punto_timbrado"
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.ruc}-{self.dv_ruc})"

    def clean(self):
        """
        Realiza validaciones personalizadas para los campos del emisor.

        Verifica la validez del RUC, DV, establecimiento, punto de expedición,
        número de timbrado, fecha de inicio de timbrado, y la coherencia
        de los rangos de numeración.
        """
        # RUC / DV
        if not (self.ruc and self.ruc.isdigit() and 7 <= len(self.ruc) <= 8):
            raise ValidationError(_("El RUC debe ser numérico de 7 u 8 dígitos."))
        if not (self.dv_ruc and self.dv_ruc.isdigit() and len(self.dv_ruc) == 1):
            raise ValidationError(_("El DV debe ser un dígito numérico."))

        # Establecimiento y Punto de Expedición
        if not (self.establecimiento and self.establecimiento.isdigit() and len(self.establecimiento) == 3):
            raise ValidationError(_("El Establecimiento debe tener 3 dígitos (ej. 001)."))
        if not (self.punto_expedicion and self.punto_expedicion.isdigit() and len(self.punto_expedicion) == 3):
            raise ValidationError(_("El Punto de expedición debe tener 3 dígitos (ej. 003)."))

        # Timbrado
        if not (self.numero_timbrado_actual and self.numero_timbrado_actual.isdigit() and len(self.numero_timbrado_actual) == 8):
            raise ValidationError(_("El Número de Timbrado debe tener exactamente 8 dígitos (ej. 02595733)."))
        if not self.fecha_inicio_timbrado:
            raise ValidationError(_("Debe indicar la fecha de inicio del timbrado (dFeIniT)."))


        # Ubicación (opcional, pero cuando se complete que sea coherente)
        if self.codigo_departamento is not None and self.codigo_departamento < 0:
            raise ValidationError(_("El código de departamento debe ser positivo."))
        if self.codigo_ciudad is not None and self.codigo_ciudad < 0:
            raise ValidationError(_("El código de ciudad debe ser positivo."))
        
                # --- VALIDACIONES DE RANGO ---
        if self.rango_numeracion_inicio > self.rango_numeracion_fin:
            raise ValidationError("El rango de numeración es inválido (inicio > fin).")

        if not (self.rango_numeracion_inicio <= self.siguiente_numero_factura <= self.rango_numeracion_fin):
            raise ValidationError(
                f"El siguiente número ({self.siguiente_numero_factura}) debe estar entre "
                f"{self.rango_numeracion_inicio} y {self.rango_numeracion_fin}."
            )
        

    def reservar_numero_y_avanzar(self):
        """
        Reserva el siguiente número de factura disponible y avanza el contador.

        Este método asegura la concurrencia segura al reservar un número
        dentro del rango definido y actualizar el `siguiente_numero_factura`.
        Debe usarse al crear un `DocumentoElectronico` propio (emisión).

        :raises ValidationError: Si no hay numeración disponible en el rango.
        :return: Una tupla con el número de factura como entero y como string de 7 dígitos.
        :rtype: tuple[int, str]
        """
        self.refresh_from_db()  # bloquea la fila del emisor
        n = self.siguiente_numero_factura
        if n > self.rango_numeracion_fin:
            raise ValidationError(
                f"No hay numeración disponible en el rango {self.rango_numeracion_inicio}–{self.rango_numeracion_fin}."
            )
        self.siguiente_numero_factura = n + 1
        self.save(update_fields=["siguiente_numero_factura"])
        return n, f"{n:07d}"

    def etiqueta_con(self, numero_int: int) -> str:
        """
        Genera la etiqueta completa del documento electrónico (ej. '001-003-0000401').

        Combina el establecimiento, punto de expedición y el número de documento
        dado para formar la etiqueta completa.

        :param numero_int: El número de documento como entero.
        :type numero_int: int
        :return: La etiqueta formateada del documento.
        :rtype: str
        """
        return f"{self.establecimiento}-{self.punto_expedicion}-{numero_int:07d}"
        
        
class DocumentoElectronico(models.Model):
    """
    Representa una factura o nota de crédito electrónica generada.

    Este modelo almacena la información detallada de un documento electrónico,
    incluyendo su tipo, numeración, estado SIFEN, fechas, y referencias a
    JSONs de la API y URLs de descarga.

    :param id: Identificador único universal del documento.
    :param emisor: Referencia al emisor que generó el documento.
    :param tipo_de: Tipo de documento electrónico (factura o nota de crédito).
    :param numero_documento: Número correlativo del documento (7 dígitos).
    :param numero_timbrado: Número de timbrado asociado al documento.
    :param cdc: Código de Control del documento (44 caracteres).
    :param estado_sifen: Estado actual del documento en el sistema SIFEN.
    :param descripcion_estado: Descripción adicional del estado.
    :param fecha_emision: Fecha y hora de emisión del documento.
    :param json_enviado_api: JSON enviado a la API de FacturaSegura.
    :param json_respuesta_api: JSON recibido como respuesta de la API.
    :param transaccion_asociada: Transacción de la casa de cambio asociada a este documento.
    :param url_kude: URL para descargar el KuDE (Representación Gráfica del Documento Electrónico).
    :param url_xml: URL para descargar el archivo XML del documento.
    """
    TIPO_DE_CHOICES = [
        ('factura', 'Factura Electrónica'),
        ('nota_credito', 'Nota de Crédito Electrónica'),
    ]

    ESTADO_SIFEN_CHOICES = [
        ('pendiente_envio', 'Pendiente de envío'),
        ('pendiente_aprobacion', 'Pendiente de Aprobación SIFEN'),
        ('pendiente_cancelacion', 'Pendiente de cancelación'),
        ('pendiente_inutilizacion', 'Pendiente de inutilización'),
        ('aprobado', 'Aprobado'),
        ('aprobado_obs', 'Aprobado con Observación'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
        ('inutilizado', 'Inutilizado'),
        ('error_api', 'Error en API Factura Segura'),
        ('error_sifen', 'Error en SIFEN'),
        ('simulado', 'Simulado (Modo Desarrollo)'),  # Para el modo de simulación
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emisor = models.ForeignKey(EmisorFacturaElectronica, on_delete=models.CASCADE, related_name='documentos_electronicos')

    tipo_de = models.CharField(max_length=20, choices=TIPO_DE_CHOICES, verbose_name="Tipo de Documento Electrónico")

    # Numeración del documento
    numero_documento = models.CharField(max_length=7, verbose_name="Número de Documento")  # Ej: 0000401
    numero_timbrado = models.CharField(max_length=8, blank=True, null=True, verbose_name="Número de Timbrado")  # dNumTim

    cdc = models.CharField(max_length=44, blank=True, null=True, unique=True, verbose_name="Código de Control (CDC)")

    estado_sifen = models.CharField(max_length=30, choices=ESTADO_SIFEN_CHOICES, default='pendiente_aprobacion', verbose_name="Estado SIFEN")
    descripcion_estado = models.TextField(blank=True, null=True, verbose_name="Descripción del Estado")

    fecha_emision = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora de Emisión")

    # JSONs de la API
    json_enviado_api = models.JSONField(blank=True, null=True, verbose_name="JSON Enviado a API")
    json_respuesta_api = models.JSONField(blank=True, null=True, verbose_name="JSON Respuesta de API")

    # Relación con Transacción (opcional)
    transaccion_asociada = models.ForeignKey(
        'transacciones.Transaccion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_electronicos',
        verbose_name="Transacción Asociada"
    )

    # URLs de descarga
    url_kude = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL de Descarga KuDE")
    url_xml = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL de Descarga XML")

    class Meta:
        verbose_name = "Documento Electrónico"
        verbose_name_plural = "Documentos Electrónicos"
        ordering = ['-fecha_emision']
        unique_together = ('emisor', 'numero_documento')

    def clean(self):
        """
        Realiza validaciones personalizadas para los campos del documento electrónico.

        Verifica que el número de documento tenga exactamente 7 dígitos numéricos.
        """
        # Validación suave: exactamente 7 dígitos (permitimos cualquier rango para poder importar/verificar XML ajenos)
        if self.numero_documento and (len(self.numero_documento) != 7 or not self.numero_documento.isdigit()):
            raise ValidationError("El número de documento debe tener exactamente 7 dígitos (con ceros a la izquierda).")

    def __str__(self):
        return f"{self.get_tipo_de_display()} Nro. {self.emisor.establecimiento}-{self.emisor.punto_expedicion}-{self.numero_documento} ({self.get_estado_sifen_display()})"


class ItemDocumentoElectronico(models.Model):
    """
    Representa un ítem dentro de un Documento Electrónico.

    Este modelo detalla cada producto o servicio incluido en un documento
    electrónico, con información como código, descripción, cantidad, precio,
    descuentos y detalles de afectación de IVA.

    :param documento_electronico: Referencia al documento electrónico al que pertenece el ítem.
    :param codigo_interno: Código interno del producto o servicio.
    :param descripcion_producto_servicio: Descripción del producto o servicio.
    :param unidad_medida: Código de la unidad de medida.
    :param cantidad: Cantidad del producto o servicio.
    :param precio_unitario: Precio unitario del producto o servicio.
    :param descuento_item: Monto de descuento aplicado a este ítem.
    :param afectacion_iva: Código de afectación del IVA.
    :param proporcion_iva: Proporción gravada del IVA.
    :param tasa_iva: Tasa de IVA aplicada.
    """
    documento_electronico = models.ForeignKey(DocumentoElectronico, on_delete=models.CASCADE, related_name='items')

    codigo_interno = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código Interno")  # dCodInt
    descripcion_producto_servicio = models.CharField(max_length=255, verbose_name="Descripción Producto/Servicio")  # dDesProSer
    unidad_medida = models.CharField(max_length=5, default="77", verbose_name="Unidad de Medida")  # cUniMed
    cantidad = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Cantidad")  # dCantProSer
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=8, verbose_name="Precio Unitario")  # dPUniProSer
    descuento_item = models.DecimalField(max_digits=15, decimal_places=8, default=0, verbose_name="Descuento por Ítem")  # dDescItem

    # Campos relacionados con IVA
    afectacion_iva = models.CharField(max_length=1, verbose_name="Código de Afectación IVA")  # iAfecIVA
    proporcion_iva = models.DecimalField(max_digits=5, decimal_places=2, default=100, verbose_name="Proporción Gravada IVA")  # dPropIVA
    tasa_iva = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="Tasa IVA")  # dTasaIVA

    class Meta:
        verbose_name = "Ítem de Documento Electrónico"
        verbose_name_plural = "Ítems de Documentos Electrónicos"
        

    def __str__(self):
        return f"{self.descripcion_producto_servicio} ({self.cantidad} x {self.precio_unitario})"
