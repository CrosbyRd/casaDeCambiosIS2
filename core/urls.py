# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Suponiendo que esta es la página principal
    path('', views.pagina_inicio_y_simulador, name='inicio'),
    # Podrías tenerla en otra URL si prefieres
    # path('simulador/', views.pagina_inicio_y_simulador, name='simulador'),
]