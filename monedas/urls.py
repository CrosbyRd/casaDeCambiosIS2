from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = "monedas"

urlpatterns = [
    path("", login_required(views.listar_monedas, login_url="/cuentas/login/"), name="listar_monedas"),
    path("crear/", login_required(views.crear_moneda, login_url="/cuentas/login/"), name="crear_moneda"),
    path("editar/<int:pk>/", login_required(views.editar_moneda, login_url="/cuentas/login/"), name="editar_moneda"),
    path("eliminar/<int:pk>/", login_required(views.eliminar_moneda, login_url="/cuentas/login/"), name="eliminar_moneda"),
    path("ver/<int:pk>/", views.moneda_detalle, name="moneda_detalle"),
]
