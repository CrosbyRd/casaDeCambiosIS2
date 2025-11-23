# operaciones/urls.py

from django.urls import path
from . import views

app_name = 'operaciones'

urlpatterns = [
    path('api/tauser/confirmar_deposito/', views.api_confirmar_deposito_tauser, name='api_confirmar_deposito_tauser'),
    path('api/tauser/resolver_variacion_tasa/', views.api_resolver_variacion_tasa, name='api_resolver_variacion_tasa'),
]
