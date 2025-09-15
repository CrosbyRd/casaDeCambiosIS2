"""Admin Panel — enrutamiento
============================

Puntos de entrada del panel de administración propio.

El *namespace* del app es ``admin_panel`` para poder referenciar
URLs como ``reverse('admin_panel:dashboard')``.

"""

from django.urls import path
from . import views

#: Espacio de nombres del app para *URL reversing*.
app_name = "admin_panel"

#: Lista de rutas públicas del módulo.
#: 
#: - ``""`` → :func:`admin_panel.views.dashboard`
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
