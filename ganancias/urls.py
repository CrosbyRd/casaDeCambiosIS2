"""
URLs de la aplicación **ganancias**.

.. module:: ganancias.urls
   :synopsis: Mapeo de rutas para el dashboard de reporte de ganancias.

Este módulo expone las rutas públicas del módulo de ganancias, en particular
el acceso al dashboard principal de análisis de ganancias por transacción.
"""


from django.urls import path
from . import views

app_name = 'ganancias'

urlpatterns = [
    path('dashboard/', views.dashboard_ganancias, name='dashboard_ganancias'),
]
