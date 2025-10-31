# pagos/integrations/router.py
from payments.stripe_service import create_payment_intent  # de tu app payments

def iniciar_pago_stripe(transaccion, email, currency='usd'):
    """
    Crea PaymentIntent para 'transaccion' y devuelve el clientSecret.
    transaccion debe poder calcular monto en USD.
    """
    usd = transaccion.monto_en_usd()          # implementa en tu core
    amount_cents = round(usd * 100)
    resp = create_payment_intent(amount_cents, currency=currency, customer_email=email)
    # OPCIONAL: guarda resp['id'] (PaymentIntent id) en transacción para conciliación
    if hasattr(transaccion, "stripe_pi_id"):
        transaccion.stripe_pi_id = resp.get('id')
        transaccion.save(update_fields=["stripe_pi_id"])
    return resp  # {'clientSecret': '...', 'id': '...'}
