# notificaciones/urls.py (NUEVO ARCHIVO)
from django.urls import path
from .views import (
    NotificacionListView,
    PreferenciasNotificacionUpdateView,
    SilenciarNotificacionView,
    MarcarLeidaNotificacionView,
)

app_name = 'notificaciones'

urlpatterns = [
    path('', NotificacionListView.as_view(), name='lista'),
    path('preferencias/', PreferenciasNotificacionUpdateView.as_view(), name='preferencias'),
    path('<uuid:pk>/silenciar/', SilenciarNotificacionView.as_view(), name='silenciar'),
    path('<uuid:pk>/leer/', MarcarLeidaNotificacionView.as_view(), name='marcar_leida'),
]
