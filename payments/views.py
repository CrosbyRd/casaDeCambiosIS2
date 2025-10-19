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


@csrf_exempt # ¡CRÍTICO! Los webhooks vienen sin token CSRF.
def stripe_webhook_view(request):
    """
    Vista que escucha las notificaciones asíncronas de Stripe (webhooks).
    
    Esta vista es llamada directamente por el SERVIDOR de Stripe, no por el
    navegador del cliente.
    
    La seguridad de esta vista depende 100% de la variable de entorno
    'STRIPE_WEBHOOK_SECRET'. Asegúrate de que esté configurada correctamente
    tanto en local (con Stripe CLI) como en producción (con Heroku).
    
    Ver las instrucciones en settings.py para más detalles.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    # La variable 'webhook_secret' se carga desde el entorno correcto
    # (settings.py lee .env en local o Config Vars en Heroku)
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET 
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Payload inválido
        print(f"ERROR: [STRIPE WEBHOOK] Invalid payload: {e}") # Mantener el print de error
        return HttpResponseBadRequest('Invalid payload', status=400)
    except stripe.error.SignatureVerificationError as e:
        # Firma inválida (¡Clave whsec_... incorrecta!)
        print(f"ERROR: [STRIPE WEBHOOK] ERROR DE FIRMA. Revisa tu STRIPE_WEBHOOK_SECRET. {e}") # Mantener el print de error
        return HttpResponseBadRequest('Invalid signature', status=400)
    except Exception as e:
        print(f"ERROR: [STRIPE WEBHOOK] Error al construir evento de Stripe: {e}") # Mantener el print de error
        return HttpResponseBadRequest('Error processing webhook', status=400)

    # Delegar el procesamiento del evento al servicio de pagos
    from pagos.services import handle_payment_webhook
    result = handle_payment_webhook(event.to_dict()) # Convertir el objeto Event a dict
    
    if result.get('status') == 'ERROR':
        print(f"ERROR: [STRIPE WEBHOOK] Error al procesar webhook en pagos.services: {result.get('message')}") # Mantener el print de error
        return JsonResponse({'error': result.get('message')}, status=500)

    return JsonResponse({'status': 'success'})
