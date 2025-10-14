# ted/urls.py
"""
Enrutamiento del módulo TED
===========================

.. module:: ted.urls
   :synopsis: URLs del kiosco y del inventario TED.

Este archivo define las rutas públicas del kiosco y las rutas de administración
para gestionar el inventario por denominación y ubicación.

El app se publica bajo el *namespace* ``ted`` cuando es incluido desde
``admin_panel/urls.py`` con:

    path("ted/", include(("ted.urls", "ted"), namespace="ted"))

De esta forma, los nombres completos quedan como:
- admin_panel:ted:inventario
- admin_panel:ted:crear_stock
- admin_panel:ted:inventario_ajustar
- admin_panel:ted:inventario_eliminar_den
- admin_panel:ted:inventario_movimientos
- admin_panel:ted:ubicaciones_disponibles
- admin_panel:ted:monedas_disponibles
"""

from django.urls import path
from . import views

app_name = "ted"

urlpatterns = [
    # ─────────────────────────────
    # Kiosco (lado usuario)
    # ─────────────────────────────
    path("", views.panel, name="panel"),
    path("operar/", views.operar, name="operar"),
    path("ticket/", views.ticket_popup, name="ticket"),

    # ─────────────────────────────
    # Inventario (admin)
    # ─────────────────────────────
    path("inventario/", views.inventario, name="inventario"),

    # Crear stock (¡nombre requerido por el template!)
    path("inventario/crear/", views.crear_stock, name="crear_stock"),
    # Alias opcional por compatibilidad con referencias antiguas
    path("inventario/crear/", views.crear_stock, name="inventario_crear"),

    # Ajustar / eliminar / movimientos
    path("inventario/ajustar/<int:den_id>/", views.inventario_ajustar, name="inventario_ajustar"),
    path("inventario/eliminar-den/<int:den_id>/", views.eliminar_denominacion, name="inventario_eliminar_den"),
    path("inventario/eliminar/<int:den_id>/", views.eliminar_denominacion, name="eliminar_denominacion"),
    path("inventario/movimientos/", views.inventario_movimientos, name="inventario_movimientos"),

    # ─────────────────────────────
    # Endpoints JSON usados por el kiosco
    # ─────────────────────────────
    path("ubicaciones_disponibles/", views.ubicaciones_disponibles, name="ubicaciones_disponibles"),
    path("monedas_disponibles/", views.monedas_disponibles, name="monedas_disponibles"),
]
