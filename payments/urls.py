# payments/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # URL para la página de previsualización
    path('checkout/preview/', views.checkout_preview_view, name='checkout_preview'),

    # URL para la página de pago dinámico
    path('pay-dynamic/', views.dynamic_payment_page_view, name='dynamic_payment_page'),

    # URL para la página de éxito
    path('payment-success/', views.payment_success_view, name='payment_success'),

    # URL para la página de pago de Stripe (maneja el client_secret)
    path('stripe-payment/', views.stripe_payment_page, name='stripe_payment_page'),
    # La URL del endpoint de la API para crear el Payment Intent ya no es necesaria aquí,
    # ya que la lógica se movió al StripeGateway.
    # path('api/create-payment-intent/', views.create_payment_intent_view, name='create_payment_intent'),
]
