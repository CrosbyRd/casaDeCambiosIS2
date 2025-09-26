# transacciones/models.py
"""
Modelos de la aplicación **transacciones**.

.. module:: transacciones.models
   :synopsis: Gestión de transacciones de compra/venta de divisas en la Casa de Cambio.

Este módulo define:

- :class:`Transaccion`: Representa operaciones de compra/venta de divisa.
  Incluye montos, monedas, tasas de cambio, comisiones, estados, medios de acreditación y validación de límites.
"""
from django.db import models
from django.conf import settings
from monedas.models import Moneda
from clientes.models import Cliente 
from operaciones.models import Tauser
import uuid
#nuevo
from django.core.exceptions import ValidationError
from configuracion.models import TransactionLimit
from django.db.models import Sum
from django.utils.timezone import now
# Forward declaration for MedioAcreditacion
class MedioAcreditacion(models.Model):
    class Meta:
        managed = False # This model is managed in the 'clientes' app
        db_table = 'clientes_medioacreditacion'

class Transaccion(models.Model):
    """
    Modelo que representa una operación de compra o venta de divisa.

    Perspectiva: Casa de Cambio.

    **Tipos de operación**
    ----------------------
    - 'venta': La empresa vende divisa al cliente (cliente compra divisa)
    - 'compra': La empresa compra divisa al cliente (cliente vende divisa)

    **Estados posibles**
    -------------------
    - 'pendiente_pago_cliente': Pendiente de pago del cliente (PYG)
    - 'pendiente_retiro_tauser': Pendiente de retiro de divisa (Tauser)
    - 'pendiente_deposito_tauser': Pendiente de depósito de divisa (Tauser)
    - 'procesando_acreditacion': Procesando acreditación a cliente (PYG)
    - 'completada': Transacción completada con éxito
    - 'cancelada': Interrumpida antes del pago/deposito del cliente
    - 'anulada': Revertida después del pago/deposito
    - 'error': Error técnico o inesperado
    """

    # --- PERSPECTIVA CASA DE CAMBIO ---
    # VENTA: La empresa VENDE divisa al cliente. (Cliente COMPRA)
    # COMPRA: La empresa COMPRA divisa al cliente. (Cliente VENDE)
    TIPO_OPERACION_CHOICES = [
        ('venta', 'Venta de Divisa'),
        ('compra', 'Compra de Divisa'),
    ]

    ESTADO_CHOICES = [
        # Estados para VENTA de divisa (Cliente Compra USD)
        ('pendiente_pago_cliente', 'Pendiente de Pago del Cliente (PYG)'),
        ('pendiente_retiro_tauser', 'Pendiente de Retiro de Divisa (Tauser)'),
        
        # Estados para COMPRA de divisa (Cliente Vende USD)
        ('pendiente_deposito_tauser', 'Pendiente de Depósito de Divisa (Tauser)'),
        ('procesando_acreditacion', 'Procesando Acreditación a Cliente (PYG)'),

        # Estados comunes
        ('completada', 'Completada'),   # Éxito
        ('cancelada', 'Cancelada'),     # Interrumpida antes del pago/deposito del cliente
        ('anulada', 'Anulada'),         # Revertida después del pago/deposito del cliente
        ('error', 'Error'),             # Error técnico/inesperado             
    ]

    # --- CAMPOS DEL MODELO ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='transacciones')
    tipo_operacion = models.CharField(max_length=10, choices=TIPO_OPERACION_CHOICES)
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES)
    
    # Montos y Monedas
    # Para VENTA: moneda_origen=PYG, moneda_destino=USD
    # Para COMPRA: moneda_origen=USD, moneda_destino=PYG
    moneda_origen = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='transacciones_origen')
    monto_origen = models.DecimalField(max_digits=15, decimal_places=2, help_text="Monto que entrega la parte que inicia.")
    
    moneda_destino = models.ForeignKey(Moneda, on_delete=models.PROTECT, related_name='transacciones_destino')
    monto_destino = models.DecimalField(max_digits=15, decimal_places=2, help_text="Monto que recibe la contraparte.")
    
    # Detalles financieros
    tasa_cambio_aplicada = models.DecimalField(max_digits=10, decimal_places=4)
    comision_aplicada = models.DecimalField(max_digits=10, decimal_places=2)

    # Información operativa
    medio_acreditacion_cliente = models.ForeignKey('clientes.MedioAcreditacion', on_delete=models.PROTECT, null=True, blank=True, help_text="Cuenta del cliente donde se acreditarán los fondos (solo en COMPRA de divisa).")
    tauser_utilizado = models.ForeignKey(Tauser, on_delete=models.PROTECT, null=True, blank=True, help_text="Terminal donde se realizó el depósito/retiro físico.")
    codigo_operacion_tauser = models.CharField(max_length=10, unique=True, help_text="Código único para que el cliente opere en el Tauser.")

    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"ID: {self.id} - {self.get_tipo_operacion_display()} para {self.cliente.username} [{self.get_estado_display()}]"

    class Meta:
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ['-fecha_creacion']
    ...
    # ----------------------------
    # Validación de límites
    # ----------------------------
    def clean(self):
        """
        Valida que el monto de la transacción no supere los límites definidos en PYG.

        Considera:
        - Límite diario y mensual del cliente.
        - Acumulado de transacciones previas (excluyendo la propia).
        """
        limite = TransactionLimit.objects.filter(moneda__codigo="PYG").first()
        if not limite:
            return  # Si no hay límite configurado, no validamos

        # --- 1. Calcular monto en PYG para esta transacción ---
        if self.moneda_origen.codigo == "PYG":
            monto_pyg = self.monto_origen
        elif self.moneda_destino.codigo == "PYG":
            monto_pyg = self.monto_destino
        else:
            # Caso raro: ninguna moneda es PYG → convertir usando tasa
            monto_pyg = self.monto_origen * self.tasa_cambio_aplicada

        # --- 2. Calcular acumulados en PYG ---
        hoy = now().date()
        inicio_mes = hoy.replace(day=1)

        acumulado_dia = Transaccion.objects.filter(
            cliente=self.cliente,
            fecha_creacion__date=hoy
        ).exclude(id=self.id).aggregate(total=Sum("monto_destino"))["total"] or 0

        acumulado_mes = Transaccion.objects.filter(
            cliente=self.cliente,
            fecha_creacion__date__gte=inicio_mes
        ).exclude(id=self.id).aggregate(total=Sum("monto_destino"))["total"] or 0

        # --- 3. Validaciones ---
        if limite.aplica_diario and acumulado_dia + monto_pyg > limite.monto_diario:
            raise ValidationError(
                f"Límite diario excedido: {acumulado_dia + monto_pyg} / {limite.monto_diario} PYG"
            )

        if limite.aplica_mensual and acumulado_mes + monto_pyg > limite.monto_mensual:
            raise ValidationError(
                f"Límite mensual excedido: {acumulado_mes + monto_pyg} / {limite.monto_mensual} PYG"
            )
