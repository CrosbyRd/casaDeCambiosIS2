"""
URLs de la aplicación **configuracion**.

.. module:: configuracion.urls
   :synopsis: Rutas para gestión de límites transaccionales y panel de configuración.

Define los endpoints principales de la aplicación, vinculando vistas CRUD
y panel principal.
"""
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
"""
Rutas definidas
---------------

1. ``""`` (root)
   - Redirige a ``configuracion:lista_limites``.
   - Usa RedirectView para no romper URLs antiguas.

2. ``limites/``
   - Muestra la lista de límites transaccionales.
   - Vista asociada: :func:`configuracion.views.lista_limites`.

3. ``limites/nuevo/``
   - Formulario para crear un nuevo límite.
   - Vista asociada: :func:`configuracion.views.crear_limite`.

4. ``limites/<int:pk>/editar/``
   - Edita un límite existente identificado por `pk`.
   - Vista asociada: :func:`configuracion.views.editar_limite`.

5. ``limites/<int:pk>/eliminar/``
   - Elimina un límite identificado por `pk`.
   - Vista asociada: :func:`configuracion.views.eliminar_limite`.

6. ``""`` (panel de configuración)
   - Muestra el panel principal de configuración.
   - Vista asociada: :func:`configuracion.views.configuracion_panel`.
"""