"""
URLs de la app Usuarios.
========================

.. module:: usuarios.urls
   :synopsis: Enrutamiento de vistas del módulo de usuarios.

Incluye rutas de autenticación, dashboard y utilidades internas.
Se añade la ruta ``/usuarios/ted/`` que renderiza la plantilla
``usuarios/ted.html`` mediante TemplateView y **endpoints de API** para el TED.
"""

from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from . import views
from . import ted_api
from . import ted_catalog

# Espacio de nombres de la app
app_name = "usuarios"

urlpatterns = [
    # --- Autoregistro y verificación ---
    path("register/", views.register, name="register"),
    path("verify/", views.verify, name="verify"),
    path("reenviar-codigo/", views.reenviar_codigo, name="reenviar_codigo"),

    # --- Redirección post-login ---
    path("login-redirect/", views.login_redirect, name="login_redirect"),

    # --- Dashboard de usuario autenticado ---
    path("dashboard/", views.dashboard, name="dashboard"),

    # --- TED (render directo de plantilla) protegido con login ---
    path(
        "ted/",
        login_required(TemplateView.as_view(template_name="usuarios/ted.html")),
        name="ted",
    ),

    # --- API TED ---
    path("ted/api/validar/", ted_api.validar_transaccion, name="ted_api_validar"),
    path("ted/api/precontar/", ted_api.precontar,           name="ted_api_precontar"),
    path("ted/api/otp/enviar/",   ted_api.otp_enviar,       name="ted_api_otp_enviar"),
    path("ted/api/otp/verificar/",ted_api.otp_verificar,    name="ted_api_otp_verificar"),
    path("ted/api/confirmar/",    ted_api.confirmar,        name="ted_api_confirmar"),
    path("ted/api/ubicaciones/",  ted_catalog.ubicaciones,  name="ted_api_ubicaciones"),
    path("ted/api/terminal/",      ted_catalog.terminal_info,   name="ted_api_terminal"),
    path("ted/ticket/<str:codigo>/", ted_api.ticket_html,   name="ted_ticket"),

    # --- Herramientas de administración internas ---
    path("admin_panel/", include(("admin_panel.urls", "admin_panel"), namespace="admin_panel")),
    path("listar/", views.listar_usuarios, name="listar_usuarios"),
    path("agregar-cliente/<int:user_id>/<uuid:cliente_id>/", views.agregar_cliente, name="agregar_cliente"),
    path("quitar-cliente/<int:user_id>/<uuid:cliente_id>/", views.quitar_cliente, name="quitar_cliente"),

    # Rutas del módulo admin_panel
    path("pagos/", include(("pagos.urls", "pagos"), namespace="pagos")),
    path("seleccionar-cliente/", views.seleccionar_cliente, name="seleccionar_cliente"),
]