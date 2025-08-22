from django.urls import path
from .views import RegisterView, CurrentUserView, UserListCreate, UserRetrieveUpdateDestroy

app_name = "usuarios"
# usuarios/urls.py
from . import views

urlpatterns = [
    path('register/', views.register, name='auth_register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    
    # Rutas para el CRUD de usuarios
    path('users/', UserListCreate.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserRetrieveUpdateDestroy.as_view(), name='user-retrieve-update-destroy'),
     path('verify/', views.verify, name='verify'),
     path('reenviar-codigo/', views.reenviar_codigo, name='reenviar_codigo'),
]

   