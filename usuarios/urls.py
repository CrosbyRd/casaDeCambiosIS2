from django.urls import path
from . import views

# Es una buena práctica definir el app_name al principio del archivo.
app_name = "usuarios"

urlpatterns = [
    # --- Rutas para Autoregistro y Verificación de Cuenta (de tu rama HEAD) ---
    # Estas son las vistas que usan plantillas HTML para que un usuario se registre.
    path('register/', views.register, name='register'),
    path('verify/', views.verify, name='verify'),
    path('reenviar-codigo/', views.reenviar_codigo, name='reenviar_codigo'),

    # --- Rutas para el Panel de Administración (de la rama entrante) ---
    # Vistas para que un administrador gestione usuarios y su relación con clientes.
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('listar/', views.listar_usuarios, name='listar_usuarios'),
    path('agregar-cliente/<int:user_id>/<uuid:cliente_id>/', views.agregar_cliente, name='agregar_cliente'),
    path('quitar-cliente/<int:user_id>/<uuid:cliente_id>/', views.quitar_cliente, name='quitar_cliente'),

]