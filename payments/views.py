# payments/views.py

import json
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .stripe_service import create_payment_intent

def checkout_preview_view(request):
    """
    Vista de previsualización de un pago.
    """
    product_name = "Suscripción Anual Gold"
    amount_in_dollars = 1.10
    
    # Pasamos el monto en centavos para evitar problemas de formato decimal
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
        # Manejar error si faltan parámetros
        return render(request, 'payment_error.html', {'message': 'Faltan parámetros para el pago de Stripe.'})

    context = {
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        'client_secret': client_secret,
        'transaction_id': transaction_id,
    }
    return render(request, 'payments/stripe_payment_page.html', context)

# La vista create_payment_intent_view ya no es necesaria,
# ya que la creación del PaymentIntent se maneja en StripeGateway.initiate_payment.
# @csrf_exempt
# def create_payment_intent_view(request):
#     ...
