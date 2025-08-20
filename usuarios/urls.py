from django.urls import path
from .views import home, RegisterView, CurrentUserView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
     path('', home, name='home'),
]