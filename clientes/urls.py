from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.ClienteListView.as_view(), name='lista'),
    path('crear/', views.ClienteCreateView.as_view(), name='crear'),
    path('<uuid:pk>/', views.ClienteDetailView.as_view(), name='detalle'),
    path('<uuid:pk>/editar/', views.ClienteUpdateView.as_view(), name='editar'),
    path('<uuid:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='eliminar'),
    path('<uuid:pk>/toggle-estado/', views.toggle_cliente_estado, name='toggle_estado'),
]