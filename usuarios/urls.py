from django.urls import path, include
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

    # --- Herramientas de administración internas ---
    path("listar/", views.listar_usuarios, name="listar_usuarios"),
    path("agregar-cliente/<int:user_id>/<uuid:cliente_id>/", views.agregar_cliente, name="agregar_cliente"),
    path("quitar-cliente/<int:user_id>/<uuid:cliente_id>/", views.quitar_cliente, name="quitar_cliente"),

    # Rutas del módulo admin_panel (si existe)
    path("admin_panel/", include("admin_panel.urls")),
    path("seleccionar-cliente/", views.seleccionar_cliente, name="seleccionar_cliente"),
]
