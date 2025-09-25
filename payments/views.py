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

@csrf_exempt
def create_payment_intent_view(request):
    """
    Crea un PaymentIntent y devuelve el client_secret.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount_in_cents = data.get('amount')
            email = data.get('email')

            if amount_in_cents is None:
                return JsonResponse({'error': 'No se proporcionó un monto.'}, status=400)

            payment_intent_data = create_payment_intent(amount_in_cents, customer_email=email)
            return JsonResponse(payment_intent_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido.'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)