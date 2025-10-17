"""
URLs de la app Usuarios.
========================

.. module:: usuarios.urls
   :synopsis: Enrutamiento de vistas del módulo de usuarios.

Incluye rutas de autenticación, dashboard y utilidades internas.
Se añade la ruta ``/usuarios/ted/`` que renderiza la plantilla
``usuarios/ted.html`` mediante TemplateView.
"""

from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required  # ← agregado
from . import views

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

    # --- Herramientas de administración internas ---
    path("listar/", views.listar_usuarios, name="listar_usuarios"),
    path("agregar-cliente/<int:user_id>/<uuid:cliente_id>/", views.agregar_cliente, name="agregar_cliente"),
    path("quitar-cliente/<int:user_id>/<uuid:cliente_id>/", views.quitar_cliente, name="quitar_cliente"),

    # Rutas del módulo admin_panel
    path("admin_panel/", include("admin_panel.urls")),
    path("seleccionar-cliente/", views.seleccionar_cliente, name="seleccionar_cliente"),
    path("pagos/", include(("pagos.urls", "pagos"), namespace="pagos")),
]
