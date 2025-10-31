# ted/urls.py
"""
Enrutamiento del módulo TED.

Este módulo define las URLs públicas del kiosco y las URLs de administración
para gestionar el inventario del Tauser (TED) por denominación y ubicación.

El app se publica bajo el *namespace* ``ted`` cuando se incluye desde
``admin_panel/urls.py`` como:

    path("ted/", include(("ted.urls", "ted"), namespace="ted"))

Nombres completos de las rutas (ejemplo):
- admin_panel:ted:inventario
- admin_panel:ted:crear_stock
- admin_panel:ted:inventario_ajustar
- admin_panel:ted:inventario_eliminar_den
- admin_panel:ted:inventario_movimientos
- admin_panel:ted:ubicaciones_disponibles
- admin_panel:ted:monedas_disponibles

Rutas definidas:
- Kiosco (lado usuario):
    - "" → panel principal del kiosco
    - "operar/" → realizar operaciones de compra/venta
    - "ticket/" → mostrar ticket de operación
- Inventario (admin):
    - "inventario/" → vista principal del inventario
    - "inventario/crear/" → crear stock de billetes
    - "inventario/eliminar-moneda/<int:moneda_id>/" → eliminar moneda completa
    - "inventario/ajustar/<int:den_id>/" → ajustar cantidad de denominación
    - "inventario/eliminar-den/<int:den_id>/" → eliminar denominación específica
    - "inventario/movimientos/" → listar movimientos del inventario
- Endpoints JSON (kiosco):
    - "ubicaciones_disponibles/" → devolver ubicaciones activas
    - "monedas_disponibles/" → devolver monedas disponibles
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
    path("inventario/eliminar-moneda/<int:moneda_id>/", views.eliminar_moneda, name="inventario_eliminar_moneda"),

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
