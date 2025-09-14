from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('', views.listar_tipos_medio_pago, name='listar_tipos_medio_pago'),
    path('agregar/', views.agregar_tipo_medio_pago, name='agregar_tipo_medio_pago'),
    path('editar/<int:pk>/', views.editar_tipo_medio_pago, name='editar_tipo_medio_pago'),
    path('eliminar/<int:pk>/', views.eliminar_tipo_medio_pago, name='eliminar_tipo_medio_pago'),

    path('ver/<int:pk>/', views.ver_tipo_medio_pago, name='ver_tipo_medio_pago'),
    path('toggle/<int:pk>/', views.toggle_activo_tipo_medio_pago, name='toggle_activo'),
]
