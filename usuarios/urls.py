from django.urls import path
from .views import AdminPanelView
from .views import (
    RegisterView, 
    CurrentUserView, 
    UserListCreate, 
    UserRetrieveUpdateDestroy, 
    AdminPanelView
)

app_name = "usuarios"

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    


    path('admin-panel/', AdminPanelView.as_view(), name='admin_panel'),
]