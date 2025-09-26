from django.urls import path
from . import views
from django.views.generic import RedirectView



app_name = "configuracion"


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="configuracion:lista_limites", permanent=False)),
    path("limites/", views.lista_limites, name="lista_limites"),
    path("limites/nuevo/", views.crear_limite, name="crear_limite"),
    path("limites/<int:pk>/editar/", views.editar_limite, name="editar_limite"),
    path("limites/<int:pk>/eliminar/", views.eliminar_limite, name="eliminar_limite"),
    path("", views.configuracion_panel, name="configuracion-panel"),
]
