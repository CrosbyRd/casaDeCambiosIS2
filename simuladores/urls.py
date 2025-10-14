# simuladores/urls.py
from django.urls import path
from . import views

app_name = 'simuladores'

urlpatterns = [
    # Endpoint API para recibir la petición inicial de pago desde el orquestador
    path('api/iniciar_pago/', views.IniciarPagoAPIView.as_view(), name='api_iniciar_pago'),

    # La página que ve el usuario para "confirmar" el pago
    path('pagina_pago/<str:transaccion_id>/', views.PaginaPagoSimuladaView.as_view(), name='pagina_pago'),
    
    # El endpoint al que el formulario de la página de pago envía la confirmación
    path('confirmar_pago/<str:transaccion_id>/', views.ConfirmarPagoSimuladoView.as_view(), name='confirmar_pago'),
]
