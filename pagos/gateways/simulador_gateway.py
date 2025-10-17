# pagos/gateways/simulador_gateway.py
import requests
from django.urls import reverse
from django.http import HttpRequest

def iniciar_pago(transaccion, request: HttpRequest):
    """
    Implementación del gateway para la pasarela simulada.

    Prepara los datos y llama al endpoint 'api_iniciar_pago' del simulador.

    Args:
        transaccion (Transaccion): La transacción a procesar.
        request (HttpRequest): La petición original para construir URLs.

    Returns:
        str: La URL de redirección a la pasarela.
        None: Si hay un error.
    """
    try:
        url_iniciar_pago = request.build_absolute_uri(reverse('simuladores:api_iniciar_pago'))
        
        url_confirmacion_webhook = request.build_absolute_uri(
            reverse('transacciones:webhook_pago_confirmado')
        )
        
        url_retorno_cliente = request.build_absolute_uri(
            reverse('transacciones:resultado_pago', args=[transaccion.id])
        )

        payload = {
            "monto": str(transaccion.monto_origen),
            "moneda": transaccion.moneda_origen.codigo,
            "referencia_comercio": str(transaccion.id),
            "descripcion": f"Compra de {transaccion.monto_destino} {transaccion.moneda_destino.codigo}",
            "url_confirmacion": url_confirmacion_webhook,
            "url_retorno": url_retorno_cliente,
        }

        response = requests.post(url_iniciar_pago, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("url_redirect")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: [Simulador Gateway] No se pudo conectar con la pasarela: {e}")
        return None
