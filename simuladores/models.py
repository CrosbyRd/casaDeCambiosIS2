# simuladores/models.py
from django.db import models
import uuid

class PagoSimulado(models.Model):
    """
    Representa una transacción de pago dentro de la pasarela simulada.

    Este modelo almacena la información necesaria para procesar un pago desde
    que se inicia hasta que se confirma, reemplazando la necesidad de un
    diccionario en memoria y haciendo el flujo más robusto y realista.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de confirmación del usuario'),
        ('PROCESADO', 'Procesado (Webhook enviado)'),
    ]

    # ID interno de la pasarela
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ID de la transacción en el sistema principal (nuestra app)
    referencia_comercio = models.UUIDField(
        help_text="El ID de la Transaccion en el sistema principal."
    )
    
    # Datos del pago
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=3)
    descripcion = models.CharField(max_length=255)

    # URLs para la comunicación
    url_confirmacion = models.URLField(
        help_text="URL (webhook) a la que se notificará el resultado del pago."
    )
    url_retorno = models.URLField(
        help_text="URL a la que se redirigirá al cliente después del pago."
    )

    # Control de estado y tiempo
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago Simulado {self.id} para {self.referencia_comercio} - {self.estado}"

    class Meta:
        verbose_name = "Pago Simulado"
        verbose_name_plural = "Pagos Simulados"
        ordering = ['-fecha_creacion']
