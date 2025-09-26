from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('calculadora/', views.calculadora_view, name='calculadora'),
    path('operacion/iniciar/', views.iniciar_operacion, name='iniciar_operacion'),
    path('operacion/confirmar/', views.confirmar_operacion, name='confirmar_operacion'),
    # NUEVO
    path('transacciones/historial/', views.historial_transacciones, name='historial_transacciones'),
]
