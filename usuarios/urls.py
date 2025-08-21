from django.urls import path
from .views import RegisterView, CurrentUserView, LoginStep1View, VerifyCodeView

app_name = "usuarios"

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('login-step1/', LoginStep1View.as_view(), name='login_step1'),       # nuevo
    path('verify-code/', VerifyCodeView.as_view(), name='verify_code'),       # nuevo
]
