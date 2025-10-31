"""
    Configuración de rutas (URLconf) para la aplicación **medios_acreditacion**.

    .. module:: medios_acreditacion.urls
    :synopsis: Rutas para la gestión de tipos de medios de acreditación (administradores)
                y de medios de acreditación de clientes (CRUD y predeterminar).

    Este módulo define todas las URL que enlazan las vistas de
    :mod:`medios_acreditacion.views`.

    **Secciones principales**
    -------------------------
    - **Tipos de medios**: CRUD para administradores.
    - **Medios de clientes**: CRUD para clientes autenticados y acción de predeterminar.
"""
from django.urls import path
from . import views

app_name = "medios_acreditacion"

urlpatterns = [
    # -----------------------------
    # Tipos de medios (admin gestiona)
    # -----------------------------
    path("tipos/", views.TipoMedioListView.as_view(), name="tipos_list"),
   
    path("tipos/crear/", views.TipoMedioCreateView.as_view(), name="tipos_create"),
    path("tipos/<uuid:pk>/editar/", views.TipoMedioUpdateView.as_view(), name="tipos_update"),
    path("tipos/<uuid:pk>/eliminar/", views.TipoMedioDeleteView.as_view(), name="tipos_delete"),
    
    # -----------------------------
    # Medios de clientes (CRUD)
    # -----------------------------
    path("clientes/", views.MedioClienteListView.as_view(), name="clientes_list"),
    path("clientes/crear/", views.MedioClienteCreateView.as_view(), name="clientes_create"),
    path("clientes/<uuid:pk>/editar/", views.MedioClienteUpdateView.as_view(), name="clientes_update"),
    path("clientes/<uuid:pk>/eliminar/", views.MedioClienteDeleteView.as_view(), name="clientes_delete"),
    path("clientes/<uuid:pk>/predeterminar/",
         views.MedioClientePredeterminarView.as_view(),
         name="clientes_predeterminar"),
]
