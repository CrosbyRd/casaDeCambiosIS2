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
    path('operacion/verificar-otp-reserva/', views.VerificarOtpReservaView.as_view(), name='verificar_otp_reserva'), # Nueva URL para Flujo A
    path('operacion/confirmacion-final/<uuid:transaccion_id>/', views.ConfirmacionFinalPagoView.as_view(), name='confirmacion_final_pago'), # Nueva URL para Flujo B
    path('transaccion/<uuid:transaccion_id>/', views.detalle_transaccion, name='detalle_transaccion'),
    path('transaccion/<uuid:transaccion_id>/iniciar-pago-stripe/', views.iniciar_pago_stripe, name='iniciar_pago_stripe'),
    path('historial/', views.historial_transacciones, name='historial_transacciones'),
    path('cancelar-transaccion/<uuid:transaccion_id>/', views.cancelar_transaccion, name='cancelar_transaccion'),
]
