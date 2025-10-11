# simuladores/models.py
from django.db import models
import uuid

class PedidoPagoSimulado(models.Model):
    """
    Almacena los datos de un pedido de pago simulado, imitando un flujo de pasarela de pagos genérica.
    Cada pedido se identifica por un hash único.
    """
    hash = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="El hash único que identifica el pedido en la pasarela.")
    
    # ID de la transacción en nuestro sistema, equivalente a un 'id_pedido_comercio'
    transaccion_id = models.CharField(max_length=36, unique=True)

    # Almacena el JSON completo enviado en la creación del pedido para referencia
    datos_pedido = models.JSONField()

    # URLs para el flujo de retorno y notificación (webhook)
    url_notificacion = models.URLField()
    url_retorno = models.URLField()

    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido Simulado: {self.hash} para Transacción: {self.transaccion_id}"

    class Meta:
        verbose_name = "Pedido de Pago Simulado"
        verbose_name_plural = "Pedidos de Pago Simulados"
        ordering = ['-fecha_creacion']
