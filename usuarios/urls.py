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
    
    # --- Rutas de la API (DRF - Combinación de ambas ramas) ---
    # Estos son los endpoints que devolverán JSON, para ser consumidos por un frontend, por ejemplo.
    # Sugerencia: Es común prefijar las rutas de la API con 'api/' para diferenciarlas.
    path('api/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('api/users/', views.UserListCreate.as_view(), name='user_list_create'),
    path('api/users/<int:pk>/', views.UserRetrieveUpdateDestroy.as_view(), name='user_retrieve_update_destroy'),
]