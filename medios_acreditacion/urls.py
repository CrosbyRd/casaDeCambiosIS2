# medios_acreditacion/urls.py
from django.urls import path
from . import views

app_name = "medios_acreditacion"

urlpatterns = [
    # Base: listado general
    path("", views.listar_tipos_medio_acreditacion, name="listar_tipos_medio_acreditacion"),
    # Alta
    path("agregar/", views.agregar_tipo_medio_acreditacion, name="agregar_tipo_medio_acreditacion"),
    # Edición
    path("editar/<int:pk>/", views.editar_tipo_medio_acreditacion, name="editar_tipo_medio_acreditacion"),
    # Eliminación (confirmación)
    path("eliminar/<int:pk>/", views.eliminar_tipo_medio_acreditacion, name="eliminar_tipo_medio_acreditacion"),
    # Detalle
    path("ver/<int:pk>/", views.ver_tipo_medio_acreditacion, name="ver_tipo_medio_acreditacion"),
    # Alternar activo/inactivo
    path("toggle/<int:pk>/", views.toggle_activo_tipo_medio_acreditacion, name="toggle_activo"),
]
