# roles/urls.py
from django.urls import path
from . import views # Importamos el módulo de vistas completo

app_name = "roles"

urlpatterns = [
    # La URL principal ahora apunta al panel de administración de roles
    path('', views.role_panel, name='role-panel'),
    
    # Nueva URL para eliminar un rol por su ID
    path('delete/<int:pk>/', views.role_delete, name='role-delete'),

    # URL para gestionar los roles de un usuario específico
    path('user/<int:user_id>/manage/', views.manage_user_roles, name='manage-user-roles'),
]
