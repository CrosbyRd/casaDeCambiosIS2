# payments/stripe_service.py

import stripe
from django.conf import settings

# Configurar la clave secreta de Stripe al iniciar
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(amount_in_cents, currency="usd", customer_email=None):
    """
    Crea un PaymentIntent en Stripe.
    - amount_in_cents: El monto a cobrar, en centavos (ej: 1000 para $10.00).
    - currency: La moneda (por defecto 'usd').
    - customer_email: Opcional, para asociar el pago a un cliente.
    """
    try:
        params = {
            'amount': amount_in_cents,
            'currency': currency,
            'automatic_payment_methods': {
                'enabled': True,
            },
        }
        if customer_email:
            # Busca si ya existe un cliente con ese email para no duplicarlo
            customers = stripe.Customer.list(email=customer_email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
            else:
                # Si no existe, lo crea
                customer = stripe.Customer.create(email=customer_email)
                customer_id = customer.id
            params['customer'] = customer_id

        intent = stripe.PaymentIntent.create(**params)
        
        # Devuelve el client_secret que el frontend necesita para confirmar el pago
        return {
            'clientSecret': intent.client_secret
        }
    except Exception as e:
        # En un caso real, aquí podrías registrar el error
        print(f"Error creating PaymentIntent: {e}")
        return {'error': str(e)}