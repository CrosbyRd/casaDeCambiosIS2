from django.urls import path
from . import views

app_name = "pagos"

urlpatterns = [
    # Admin – Tipos de medios
    path("tipos/", views.TipoPagoListView.as_view(), name="tipos_list"),
    path("tipos/crear/", views.TipoPagoCreateView.as_view(), name="tipos_create"),
    path("tipos/<uuid:id_tipo>/editar/", views.TipoPagoUpdateView.as_view(), name="tipos_update"),
    path("tipos/<uuid:id_tipo>/eliminar/", views.TipoPagoDeleteView.as_view(), name="tipos_delete"),

    # Cliente – Medios
    path("clientes/", views.MedioPagoListView.as_view(), name="clientes_list"),
    path("clientes/crear/", views.MedioPagoCreateView.as_view(), name="clientes_create"),
    path("clientes/<uuid:id_medio>/editar/", views.MedioPagoUpdateView.as_view(), name="clientes_update"),
    path("clientes/<uuid:id_medio>/eliminar/", views.MedioPagoDeleteView.as_view(), name="clientes_delete"),
    path("clientes/<uuid:id_medio>/predeterminar/", views.MedioPagoPredeterminarView.as_view(), name="clientes_predeterminar"),
]