from django.urls import path
from . import views

app_name = "medios_acreditacion"

urlpatterns = [
    path("", views.listar_categorias, name="listar_categorias"),
    path("agregar/", views.agregar_categoria, name="agregar_categoria"),
    path("editar/<int:pk>/", views.editar_categoria, name="editar_categoria"),
    path("eliminar/<int:pk>/", views.eliminar_categoria, name="eliminar_categoria"),
    path("ver/<int:pk>/", views.ver_categoria, name="ver_categoria"),
    path("toggle/<int:pk>/", views.toggle_activo, name="toggle_activo"),
]
