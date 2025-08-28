

from django.urls import path
from . import views
app_name = "cotizaciones"
urlpatterns = [
    path('', views.cotizacion_list, name='cotizacion_list'),
    path('crear/', views.cotizacion_create, name='cotizacion_create'),
    path('editar/<int:pk>/', views.cotizacion_update, name='cotizacion_update'),
    path('eliminar/<int:pk>/', views.cotizacion_delete, name='cotizacion_delete'),
]
