# simuladores/urls.py
from django.urls import path
from . import views

app_name = 'simuladores'

urlpatterns = [
    # La URL para 'api_iniciar_pago' ya no es necesaria, ya que la lógica
    # se ha movido al LocalGateway.
    # path('api/iniciar_pago/', views.IniciarPagoAPIView.as_view(), name='api_iniciar_pago'),

    # La página que ve el usuario para "confirmar" el pago
    path('pagina_pago/<str:transaccion_id>/', views.PaginaPagoSimuladaView.as_view(), name='pagina_pago'),
    
    # El endpoint al que el formulario de la página de pago envía la confirmación
    path('confirmar_pago/<str:transaccion_id>/', views.ConfirmarPagoSimuladoView.as_view(), name='confirmar_pago'),
]
