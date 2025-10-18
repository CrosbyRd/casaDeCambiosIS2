# payments/stripe_service.py

import stripe
from django.conf import settings

# Configurar la clave secreta de Stripe al iniciar
stripe.api_key = settings.STRIPE_SECRET_KEY

# No necesitamos reverse ni urlencode aquí si return_url se maneja en el frontend
# from django.urls import reverse
# from urllib.parse import urlencode

def create_payment_intent(amount_in_cents, currency="usd", customer_email=None, transaction_id=None):
    """
    Crea un PaymentIntent en Stripe.
    - amount_in_cents: El monto a cobrar, en centavos (ej: 1000 para $10.00).
    - currency: La moneda (por defecto 'usd').
    - customer_email: Opcional, para asociar el pago a un cliente.
    - transaction_id: Opcional, ID de la transacción interna para metadata.
    """
    try:
        params = {
            'amount': amount_in_cents,
            'currency': currency,
            'automatic_payment_methods': {
                'enabled': True,
            },
            # Eliminamos 'return_url' de aquí
            # 'return_url': settings.SITE_URL + reverse('payments:payment_success') + '?' + urlencode({'transaction_id': str(transaction_id)}),
        }
        if customer_email:
            customers = stripe.Customer.list(email=customer_email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
            else:
                customer = stripe.Customer.create(email=customer_email)
                customer_id = customer.id
            params['customer'] = customer_id
        
        if transaction_id:
            params['metadata'] = {'transaccion_id': str(transaction_id)} # Usar 'transaccion_id' para consistencia con el feedback
        
        intent = stripe.PaymentIntent.create(**params)
        
        return {
            'clientSecret': intent.client_secret
        }
    except Exception as e:
        print(f"Error creating PaymentIntent: {e}") # Mantener el print de error
        return {'error': str(e)}

def handle_webhook(payload: dict):
    """
    Maneja los eventos de webhook de Stripe.
    Actualiza el estado de la transacción en la base de datos.
    """
    from transacciones.models import Transaccion # Importar aquí para evitar circular imports

    event_type = payload.get('type')
    data_object = payload.get('data', {}).get('object', {})
    
    # Extraer el ID de la transacción de nuestra base de datos
    # Asumimos que el PaymentIntent o Checkout Session contiene una referencia a nuestro transaction_id
    # Esto puede variar dependiendo de cómo se haya implementado la referencia en el PaymentIntent metadata
    # Por ahora, asumiremos que el 'metadata' del PaymentIntent contiene 'transaction_id'
    transaction_id = data_object.get('metadata', {}).get('transaction_id')
    payment_intent_id = data_object.get('id') # ID del PaymentIntent

    if not transaction_id:
        print(f"ERROR: [STRIPE WEBHOOK] Webhook {event_type} recibido sin transaction_id en metadata. PaymentIntent ID: {payment_intent_id}")
        return {'status': 'ERROR', 'message': 'transaction_id no encontrado en metadata.'}

    try:
        transaccion = Transaccion.objects.get(id=transaction_id)
    except Transaccion.DoesNotExist:
        print(f"ERROR: [STRIPE WEBHOOK] Transacción {transaction_id} no encontrada para PaymentIntent {payment_intent_id}.")
        return {'status': 'ERROR', 'message': 'Transacción no encontrada.'}

    # Procesar diferentes tipos de eventos de Stripe
    if event_type == 'payment_intent.succeeded':
        if transaccion.estado == 'pendiente_pago_stripe':
            transaccion.estado = 'pendiente_retiro_tauser' # O el estado final después de un pago exitoso
            transaccion.save(update_fields=['estado'])
            print(f"INFO: [STRIPE WEBHOOK] Transacción {transaccion.id} (PaymentIntent {payment_intent_id}) actualizada a 'pendiente_retiro_tauser'.")
            return {'status': 'EXITOSO', 'message': 'Pago exitoso y transacción actualizada.'}
        else:
            print(f"WARN: [STRIPE WEBHOOK] PaymentIntent {payment_intent_id} (Transacción {transaccion.id}) ya no estaba en estado 'pendiente_pago_stripe'. Estado actual: {transaccion.estado}")
            return {'status': 'EXITOSO', 'message': 'Pago exitoso, pero transacción ya procesada.'}
    
    elif event_type == 'payment_intent.payment_failed':
        if transaccion.estado == 'pendiente_pago_stripe':
            transaccion.estado = 'cancelada' # O un estado de fallo específico
            transaccion.save(update_fields=['estado'])
            print(f"INFO: [STRIPE WEBHOOK] Transacción {transaccion.id} (PaymentIntent {payment_intent_id}) actualizada a 'cancelada' por fallo de pago.")
            return {'status': 'RECHAZADO', 'message': 'Pago fallido y transacción cancelada.'}
        else:
            print(f"WARN: [STRIPE WEBHOOK] PaymentIntent {payment_intent_id} (Transacción {transaccion.id}) falló, pero transacción ya no estaba en estado 'pendiente_pago_stripe'. Estado actual: {transaccion.estado}")
            return {'status': 'RECHAZADO', 'message': 'Pago fallido, pero transacción ya procesada.'}

    # Otros eventos de PaymentIntent que podrían ser relevantes:
    # payment_intent.processing, payment_intent.canceled, payment_intent.requires_action

    print(f"INFO: [STRIPE WEBHOOK] Evento de Stripe {event_type} no manejado explícitamente para PaymentIntent {payment_intent_id}.")
    return {'status': 'IGNORADO', 'message': f'Evento {event_type} no manejado.'}
