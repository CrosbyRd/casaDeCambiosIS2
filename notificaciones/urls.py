# notificaciones/urls.py (NUEVO ARCHIVO)
"""
Módulo de enrutamiento de la aplicación de notificaciones.

Define las rutas (URLs) que permiten acceder a las vistas relacionadas con la gestión
de notificaciones y las preferencias del usuario en el sistema Global Exchange.


"""

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
