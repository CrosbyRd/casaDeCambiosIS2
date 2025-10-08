# ted/urls.py — REEMPLAZO COMPLETO
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

    # Crear stock (nombre “nuevo” + alias legacy), apuntando a views.crear_stock
    path("inventario/crear/", views.crear_stock, name="inventario_crear_stock"),
    path("inventario/crear/", views.crear_stock, name="crear_stock"),  # alias
    path("inventario/crear/<int:moneda_id>/", views.crear_stock, name="inventario_crear_stock_moneda"),

    # Ajustar stock
    path("inventario/ajustar/<int:den_id>/", views.inventario_ajustar, name="inventario_ajustar"),

    # Eliminar denominación (nombre “nuevo” + alias legacy), apuntando a views.eliminar_denominacion
    path("inventario/eliminar-den/<int:den_id>/", views.eliminar_denominacion, name="inventario_eliminar_den"),
    path("inventario/eliminar/<int:den_id>/", views.eliminar_denominacion, name="eliminar_denominacion"),

    # Movimientos
    path("inventario/movimientos/", views.inventario_movimientos, name="inventario_movimientos"),

    # ──────────────────────────────────────────────────────────────────────────
    # NUEVO: Endpoint JSON para el modal de usuario (monedas disponibles)
    # ──────────────────────────────────────────────────────────────────────────
    path("monedas_disponibles/", views.monedas_disponibles, name="monedas_disponibles"),
]
