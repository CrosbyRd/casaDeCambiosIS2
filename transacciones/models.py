# transacciones/models.py

from django.db import models
from django.conf import settings
from monedas.models import Moneda
from clientes.models import Cliente 
from operaciones.models import Tauser
import uuid

# Forward declaration for MedioAcreditacion
class MedioAcreditacion(models.Model):
    class Meta:
        managed = False # This model is managed in the 'clientes' app
        db_table = 'clientes_medioacreditacion'

class Transaccion(models.Model):
    """
    Modela una operación de compra o venta de divisa.
    La perspectiva es siempre desde la Casa de Cambio.
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
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('error', 'Error'),
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
