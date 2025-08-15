"""
URL configuration for CasaDeCambioIS2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render


urlpatterns = [
    path("lib/", include("lib.urls")),
    path('admin/', admin.site.urls),
    path('', include('users.urls')), # Incluye las URLs de la app de usuarios
    # Ruta para el login, usando la vista de Django
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    # Ruta para el logout
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    # Ruta de la página principal (dashboard) que redirige al login si no está autenticado
    path('', lambda request: redirect('dashboard_simple'), name='home'),
    path('dashboard/', lambda request: render(request,'users/templates/users/dashboard_simple.html'), name='dashboard_simple'),
]
