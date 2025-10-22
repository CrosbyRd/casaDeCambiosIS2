from django.db import models
from django.conf import settings
import uuid
from django.contrib.postgres.fields import JSONField  # Para almacenar JSON de la API
from django.utils import timezone

class EmisorFacturaElectronica(models.Model):
    """
    Almacena la configuración del emisor de facturas electrónicas.
    """
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Emisor")
    ruc = models.CharField(max_length=15, verbose_name="RUC del Emisor")
    dv_ruc = models.CharField(max_length=1, verbose_name="Dígito Verificador del RUC")
    email_emisor = models.EmailField(verbose_name="Email del Emisor")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    numero_casa = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número de Casa")
    codigo_departamento = models.CharField(max_length=5, blank=True, null=True, verbose_name="Código Departamento")
    descripcion_departamento = models.CharField(max_length=50, blank=True, null=True, verbose_name="Descripción Departamento")
    codigo_ciudad = models.CharField(max_length=5, blank=True, null=True, verbose_name="Código Ciudad")
    descripcion_ciudad = models.CharField(max_length=50, blank=True, null=True, verbose_name="Descripción Ciudad")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=False, verbose_name="Emisor Activo")  # Nuevo campo

    # Datos específicos de la numeración
    establecimiento = models.CharField(max_length=3, default="001", verbose_name="Establecimiento")
    punto_expedicion = models.CharField(max_length=3, default="003", verbose_name="Punto de Expedición")
    numero_timbrado_actual = models.CharField(max_length=8, blank=True, null=True, verbose_name="Número de Timbrado Actual")
    # Fecha de inicio del timbrado (útil para dFeIniT si la API lo requiere)
    fecha_inicio_timbrado = models.DateField(blank=True, null=True, verbose_name="Fecha de Inicio de Timbrado")

    # Rango de numeración asignado por equipo/email
    email_equipo = models.EmailField(unique=True, verbose_name="Email del Equipo Asignado")
    rango_numeracion_inicio = models.IntegerField(verbose_name="Inicio del Rango de Numeración")
    rango_numeracion_fin = models.IntegerField(verbose_name="Fin del Rango de Numeración")
    siguiente_numero_factura = models.IntegerField(verbose_name="Siguiente Número de Factura Disponible")

    # Token de autenticación de Factura Segura
    auth_token = models.CharField(max_length=500, blank=True, null=True, verbose_name="Authentication Token API")
    token_generado_at = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Generación del Token")

    # Actividades económicas (JSONField para flexibilidad)
    actividades_economicas = models.JSONField(default=list, blank=True, null=True, verbose_name="Actividades Económicas")

    class Meta:
        verbose_name = "Emisor de Factura Electrónica"
        verbose_name_plural = "Emisores de Facturas Electrónicas"

    def __str__(self):
        return f"{self.nombre} ({self.ruc})"


class DocumentoElectronico(models.Model):
    """
    Representa una factura o nota de crédito electrónica generada.
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
    emisor = models.ForeignKey(EmisorFacturaElectronica, on_delete=models.PROTECT, related_name='documentos_electronicos')

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

    def __str__(self):
        return f"{self.get_tipo_de_display()} Nro. {self.emisor.establecimiento}-{self.emisor.punto_expedicion}-{self.numero_documento} ({self.get_estado_sifen_display()})"


class ItemDocumentoElectronico(models.Model):
    """
    Representa un ítem dentro de un Documento Electrónico.
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
