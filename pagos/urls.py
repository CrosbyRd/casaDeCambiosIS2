"""
Este módulo define las rutas URL del aplicativo **Pagos**, que maneja tanto la gestión
de tipos de medios de pago (nivel administrador) como los medios de pago de los clientes.

Las vistas asociadas se encuentran en ``pagos.views``.

.. module:: pagos.urls
   :synopsis: Rutas URL para la aplicación de pagos.

.. topic:: Rutas definidas

   - **tipos_list** → Lista todos los tipos de medios de pago (vista de administración).
   - **tipos_create** → Permite crear un nuevo tipo de medio de pago.
   - **tipos_update** → Permite editar un tipo de medio de pago existente.
   - **tipos_delete** → Elimina un tipo de medio de pago existente.
   - **clientes_list** → Lista los medios de pago registrados por un cliente.
   - **clientes_create** → Permite registrar un nuevo medio de pago del cliente.
   - **clientes_update** → Permite editar un medio de pago del cliente.
   - **clientes_delete** → Elimina un medio de pago del cliente.
   - **clientes_predeterminar** → Marca un medio de pago del cliente como predeterminado.
"""
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