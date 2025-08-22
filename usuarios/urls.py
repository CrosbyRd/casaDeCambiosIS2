from django.urls import path
from .views import RegisterView, CurrentUserView, UserListCreate, UserRetrieveUpdateDestroy
from .import views

app_name = "usuarios"

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('admin-panel/', views.admin_panel,  name='admin_panel'),
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/agregar/<int:user_id>/<uuid:cliente_id>/', views.agregar_cliente, name='agregar_cliente'),
    path('usuarios/quitar/<int:user_id>/<uuid:cliente_id>/', views.quitar_cliente, name='quitar_cliente'),
]