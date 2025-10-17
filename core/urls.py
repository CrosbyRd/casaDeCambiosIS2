# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Asumo que tienes otras URLs aquí, como la página de inicio
    path('calculadora/', views.calculadora_view, name='calculadora'),
    path('tasas/', views.site_rates, name='tasas'),
    path('operacion/iniciar/', views.iniciar_operacion, name='iniciar_operacion'),
    path('operacion/confirmar/', views.confirmar_operacion, name='confirmar_operacion'),
    
    # --- MODIFICADO: Cambiado de <int:...> a <uuid:...> ---
    path('transaccion/<uuid:transaccion_id>/', views.detalle_transaccion, name='detalle_transaccion'),
    path('transaccion/<uuid:transaccion_id>/iniciar-pago-stripe/', views.iniciar_pago_stripe, name='iniciar_pago_stripe'),
    # ----------------------------------------------------

    path('historial/', views.historial_transacciones, name='historial_transacciones'),
]