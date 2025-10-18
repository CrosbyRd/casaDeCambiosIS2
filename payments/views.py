# payments/views.py
import json
import stripe # Importar la librería stripe
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .stripe_service import create_payment_intent
# --- NUEVO: Importar el modelo Transaccion ---
from transacciones.models import Transaccion

def checkout_preview_view(request):
    """
    Vista de previsualización de un pago.
    """
    product_name = "Suscripción Anual Gold"
    amount_in_dollars = 1.10
    
    amount_in_cents = int(amount_in_dollars * 100)

    context = {
        'product_name': product_name,
        'amount_display': amount_in_dollars,
        'amount_cents_for_url': amount_in_cents
    }
    return render(request, 'checkout_preview.html', context)

def dynamic_payment_page_view(request):
    """
    Renderiza la página de pago con monto dinámico.
    """
    context = {
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
    }
    return render(request, 'dynamic_payment.html', context)

def payment_success_view(request):
    """
    Renderiza la página de éxito tras un pago.
    """
    return render(request, 'payment_success.html')

def stripe_payment_page(request):
    """
    Renderiza una página para que el cliente complete el pago con Stripe
    usando el client_secret.
    """
    client_secret = request.GET.get('client_secret')
    transaction_id = request.GET.get('transaction_id')

    if not client_secret or not transaction_id:
        return HttpResponseBadRequest("Faltan parámetros para el pago.")

    # --- MODIFICADO: Buscamos la transacción para mostrar sus detalles ---
    try:
        transaccion = get_object_or_404(Transaccion, id=transaction_id)
    except Transaccion.DoesNotExist:
        return HttpResponseBadRequest("La transacción especificada no existe.")

    context = {
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        'client_secret': client_secret,
        'transaccion': transaccion, # Pasamos el objeto completo al template
    }
    return render(request, 'payments/stripe_payment_page.html', context)


@csrf_exempt
def stripe_webhook_view(request):
    """
    Vista para recibir y procesar webhooks de Stripe.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # Aquí deberías usar tu clave de endpoint de webhook de Stripe
        # settings.STRIPE_WEBHOOK_SECRET
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        print(f"ERROR: [STRIPE WEBHOOK] Invalid payload: {e}")
        return HttpResponseBadRequest('Invalid payload', status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"ERROR: [STRIPE WEBHOOK] Invalid signature: {e}")
        return HttpResponseBadRequest('Invalid signature', status=400)
    except Exception as e:
        print(f"ERROR: [STRIPE WEBHOOK] Error al construir evento de Stripe: {e}")
        return HttpResponseBadRequest('Error processing webhook', status=400)

    # Delegar el procesamiento del evento al servicio de pagos
    from pagos.services import handle_payment_webhook
    result = handle_payment_webhook(event.to_dict()) # Convertir el objeto Event a dict
    
    if result.get('status') == 'ERROR':
        print(f"ERROR: [STRIPE WEBHOOK] Error al procesar webhook en pagos.services: {result.get('message')}")
        return JsonResponse({'error': result.get('message')}, status=500)

    return JsonResponse({'status': 'success'})
