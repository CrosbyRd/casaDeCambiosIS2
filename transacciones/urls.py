# transacciones/urls.py
from django.urls import path
from . import views

app_name = 'transacciones'

urlpatterns = [
    path('comprar/', views.IniciarCompraDivisaView.as_view(), name='iniciar_compra'),
    path('iniciar_pago/<uuid:transaccion_id>/', views.IniciarPagoTransaccionView.as_view(), name='iniciar_pago'),
    # URL del webhook que recibe la confirmación de pago desde la pasarela
    path('webhook/pago_confirmado/', views.WebhookConfirmacionPagoView.as_view(), name='webhook_pago_confirmado'),

    # URL de la página de resultado a la que se redirige al cliente
    path('resultado/<uuid:transaccion_id>/', views.ResultadoPagoView.as_view(), name='resultado_pago'),

    path('cancelar-por-tasa/<uuid:transaccion_id>/', views.cancelar_por_tasa, name='cancelar_por_tasa'),#notificacion
]
