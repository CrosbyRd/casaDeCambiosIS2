"""Admin Panel — enrutamiento
============================

Puntos de entrada del panel de administración propio.

El *namespace* del app es ``admin_panel`` para poder referenciar
URLs como ``reverse('admin_panel:dashboard')``.

"""
# admin_panel/urls.py
from django.urls import path, include
from . import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # monta TED bajo /admin_panel/ted/ con namespace "tedavs"
    path("ted/", include(("ted.urls", "ted"), namespace="ted")),
]

