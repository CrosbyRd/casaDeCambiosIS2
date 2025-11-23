"""
==================================
Módulo urls de la app monedas
==================================

Este módulo define las rutas de la aplicación ``monedas``.  
Cada URL se asocia a una vista correspondiente en :mod:`monedas.views`.  
Las vistas requieren autenticación para acceder, excepto el detalle de moneda 
que igualmente valida permisos en la vista.

Contenido
---------
- ``listar_monedas``: Lista todas las monedas registradas.
- ``crear_moneda``: Formulario para crear una nueva moneda.
- ``editar_moneda``: Formulario para editar una moneda existente.
- ``eliminar_moneda``: Confirma y elimina una moneda.
- ``moneda_detalle``: Muestra la información detallada de una moneda.

Constantes
----------
- :data:`app_name`: Define el namespace de la aplicación.
- :data:`urlpatterns`: Lista de rutas URL.
"""

from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

#: Namespace de la aplicación ``monedas``.
app_name = "monedas"

#: Definición de patrones de URL para la aplicación ``monedas``.
urlpatterns = [
    path(
        "",
        login_required(views.listar_monedas, login_url="/cuentas/login/"),
        name="listar_monedas"
    ),
    path(
        "crear/",
        login_required(views.crear_moneda, login_url="/cuentas/login/"),
        name="crear_moneda"
    ),
    path(
        "editar/<int:pk>/",
        login_required(views.editar_moneda, login_url="/cuentas/login/"),
        name="editar_moneda"
    ),
    path(
        "eliminar/<int:pk>/",
        login_required(views.eliminar_moneda, login_url="/cuentas/login/"),
        name="eliminar_moneda"
    ),
    path(
        "ver/<int:pk>/",
        views.moneda_detalle,
        name="moneda_detalle"
    ),
]
