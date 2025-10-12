# simuladores/urls.py

from django.urls import path
from . import views

app_name = 'simuladores'

urlpatterns = [
    # Endpoint para recibir la petición inicial de pago (Paso 1)
    path('api/iniciar_pago/', views.IniciarPagoAPIView.as_view(), name='api_iniciar_pago'),

    # La página de checkout que ve el usuario (Paso 2)
    path('pagina_pago/<uuid:hash>/', views.PaginaPagoSimuladaView.as_view(), name='pagina_pago'),
    
    # El endpoint al que el formulario de la página de pago envía la confirmación (Procesa el pago y notifica)
    path('confirmar_pago/<uuid:hash>/', views.ConfirmarPagoSimuladoView.as_view(), name='confirmar_pago'),
]
