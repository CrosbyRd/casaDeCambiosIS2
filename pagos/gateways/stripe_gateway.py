from django.http import HttpRequest
from transacciones.models import Transaccion
from .base import BasePaymentGateway
import stripe
from django.conf import settings
from django.urls import reverse

# Configurar la clave secreta de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeGateway(BasePaymentGateway):
    """
    Implementación de la pasarela de pago Stripe.
    """

    def initiate_payment(self, transaccion: Transaccion, request: HttpRequest) -> str:
        """
        Inicia un proceso de pago con Stripe para una transacción dada.
        Devuelve la URL a la que el cliente debe ser redirigido para completar el pago.
        """
        try:
            amount_in_cents = int(transaccion.monto_origen * 100)
            currency = transaccion.moneda_origen.codigo.lower()

            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                metadata={'transaccion_id': str(transaccion.id)},
                automatic_payment_methods={'enabled': True},
            )
            
            # Redirigir a una página interna que maneje el client_secret de Stripe
            # y muestre el widget de pago.
            # Asumimos que existe una URL en 'payments' para esto.
            # Por ejemplo: payments:stripe_payment_page
            return reverse('payments:stripe_payment_page') + f'?client_secret={intent.client_secret}&transaction_id={transaccion.id}'

        except Exception as e:
            print(f"Error al iniciar pago con Stripe: {e}")
            # En un entorno real, se manejaría el error de forma más robusta
            return "" # Devolver una cadena vacía o una URL de error

    def handle_webhook(self, payload: dict) -> dict:
        """
        Maneja una notificación de webhook de Stripe.
        """
        # Lógica para verificar la firma del webhook y procesar el evento
        # Por ahora, una implementación básica.
        event_type = payload.get('type')
        if event_type == 'payment_intent.succeeded':
            # Procesar pago exitoso
            return {'status': 'EXITOSO', 'transaccion_id': payload['data']['object']['metadata']['transaccion_id']}
        elif event_type == 'payment_intent.payment_failed':
            # Procesar pago fallido
            return {'status': 'RECHAZADO', 'transaccion_id': payload['data']['object']['metadata']['transaccion_id']}
        
        return {'status': 'IGNORADO'} # Otros eventos
