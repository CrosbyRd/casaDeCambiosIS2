"""Rutas URL de la aplicación *pagos*.

Expone las vistas para **listar**, **crear**, **editar**, **eliminar**, **ver detalle**
y **alternar el estado** (activo/inactivo) de los Tipos de Medio de Pago.

.. rubric:: Nombres de las rutas

- ``pagos:listar_tipos_medio_pago``
- ``pagos:agregar_tipo_medio_pago``
- ``pagos:editar_tipo_medio_pago``
- ``pagos:eliminar_tipo_medio_pago``
- ``pagos:ver_tipo_medio_pago``
- ``pagos:toggle_activo``
"""
from django.urls import path
from . import views

app_name = "pagos"

urlpatterns = [
    # Listado general
    path("", views.listar_tipos_medio_pago, name="listar_tipos_medio_pago"),
    # Alta
    path("agregar/", views.agregar_tipo_medio_pago, name="agregar_tipo_medio_pago"),
    # Edición
    path("editar/<int:pk>/", views.editar_tipo_medio_pago, name="editar_tipo_medio_pago"),
    # Eliminación (con confirmación)
    path("eliminar/<int:pk>/", views.eliminar_tipo_medio_pago, name="eliminar_tipo_medio_pago"),
    # Detalle
    path("ver/<int:pk>/", views.ver_tipo_medio_pago, name="ver_tipo_medio_pago"),
    # Alternar estado activo/inactivo
    path("toggle/<int:pk>/", views.toggle_activo_tipo_medio_pago, name="toggle_activo"),
]
