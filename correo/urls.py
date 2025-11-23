from django.urls import path, include

urlpatterns = [
    path("signup/", include("usuarios.urls", namespace="usuarios")),
]
