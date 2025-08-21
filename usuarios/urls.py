from django.urls import path
from .views import RegisterView, CurrentUserView, UserListCreate, UserRetrieveUpdateDestroy
from . import views

app_name = "usuarios"

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    
    # Rutas para el CRUD de usuarios
    path('users/', UserListCreate.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserRetrieveUpdateDestroy.as_view(), name='user-retrieve-update-destroy'),

    path('admin-menu/', views.admin_menu, name='admin-menu')
]