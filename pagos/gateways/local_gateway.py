from django.http import HttpRequest
from transacciones.models import Transaccion
from .base import BasePaymentGateway
from django.urls import reverse
import json
import requests
from simuladores.models import PagoSimulado # Importar el modelo PagoSimulado

class LocalGateway(BasePaymentGateway):
    """
    Implementación de la pasarela de pago local simulada.
    """

    def initiate_payment(self, transaccion: Transaccion, request: HttpRequest) -> str:
        """
        Inicia un proceso de pago con la pasarela local simulada.
        Devuelve la URL a la que el cliente debe ser redirigido para completar el pago.
        """
        try:
            # Crear un registro de PagoSimulado
            pago = PagoSimulado.objects.create(
                referencia_comercio=transaccion.id,
                monto=transaccion.monto_origen,
                moneda=transaccion.moneda_origen.codigo,
                descripcion=f"Pago por transacción {transaccion.id}",
                url_confirmacion=request.build_absolute_uri(reverse('transacciones:webhook_confirmacion_pago')),
                url_retorno=request.build_absolute_uri(reverse('transacciones:resultado_pago', args=[transaccion.id]))
            )
            
            # Redirigir a la página de pago del simulador
            return reverse('simuladores:pagina_pago', args=[pago.id])

        except Exception as e:
            print(f"Error al iniciar pago con pasarela local: {e}")
            return "" # Devolver una cadena vacía o una URL de error

    def handle_webhook(self, payload: dict) -> dict:
        """
        Maneja una notificación de webhook de la pasarela local simulada.
        """
        # La lógica de webhook para la pasarela local ya está en transacciones/views.py
        # Este método aquí es más bien un placeholder o para una futura expansión
        # donde el gateway local podría tener su propia lógica de procesamiento de webhooks.
        # Por ahora, simplemente devolveremos el payload tal cual, asumiendo que
        # el orquestador o la vista de webhook principal lo procesará.
        
        # Para mantener la compatibilidad con la interfaz, simularemos el procesamiento.
        estado_pago = payload.get('estado')
        transaccion_id = payload.get('referencia_comercio')

        if estado_pago == 'EXITOSO':
            return {'status': 'EXITOSO', 'transaccion_id': transaccion_id}
        elif estado_pago == 'RECHAZADO':
            return {'status': 'RECHAZADO', 'transaccion_id': transaccion_id}
        
        return {'status': 'IGNORADO'}
