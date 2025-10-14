# ted/urls.py
from django.urls import path
from . import views

app_name = "ted"

urlpatterns = [
    # Terminal (usuario)
    path("", views.panel, name="panel"),
    path("operar/", views.operar, name="operar"),
    path("ticket/", views.ticket_popup, name="ticket"),
    path("cheque/", views.cheque_mock, name="cheque_mock"),

    # Inventario (admin)
    path("inventario/", views.inventario, name="inventario"),

    # Crear stock
    # Usamos el nombre que tu plantilla ya espera: 'crear_stock'
    path("inventario/crear/", views.crear_stock, name="crear_stock"),
    # Alias opcional por compatibilidad (si en algún lugar lo usaste):
    path("inventario/crear/", views.crear_stock, name="inventario_crear"),

    # Ajustar stock
    path("inventario/ajustar/<int:den_id>/", views.inventario_ajustar, name="inventario_ajustar"),

    # Eliminar denominación (alias “nuevo” y legacy apuntan al mismo view)
    path("inventario/eliminar-den/<int:den_id>/", views.eliminar_denominacion, name="inventario_eliminar_den"),
    path("inventario/eliminar/<int:den_id>/", views.eliminar_denominacion, name="eliminar_denominacion"),

    # Movimientos
    path("inventario/movimientos/", views.inventario_movimientos, name="inventario_movimientos"),

    # Endpoint JSON (para el modal del usuario: monedas habilitadas)
    path("monedas_disponibles/", views.monedas_disponibles, name="monedas_disponibles"),
]
