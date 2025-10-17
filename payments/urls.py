# payments/urls.py
from django.urls import path
from . import views

# --- AÑADIDO: Asegúrate de tener el app_name ---
app_name = 'payments'
# ---------------------------------------------

urlpatterns = [
    # URL para la página de previsualización
    path('checkout/preview/', views.checkout_preview_view, name='checkout_preview'),

    # URL para la página de pago dinámico
    path('pay-dynamic/', views.dynamic_payment_page_view, name='dynamic_payment_page'),

    # URL para la página de éxito
    path('payment-success/', views.payment_success_view, name='payment_success'),

    # URL para la página de pago de Stripe (esta es la que usamos)
    path('stripe-payment/', views.stripe_payment_page, name='stripe_payment_page'),
]