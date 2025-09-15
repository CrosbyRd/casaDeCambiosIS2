"""Admin Panel — vistas
======================

Vistas protegidas del panel de administración propio.

Requisitos de acceso
--------------------
Todas las vistas deben estar autenticadas con :func:`django.contrib.auth.decorators.login_required`
y, en el caso del *dashboard*, además requieren el permiso
``admin_panel.access_admin_dashboard``.

"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Dashboard del Admin Panel.

    Vista principal del panel. Verifica que el usuario autenticado cuente con el
    permiso ``admin_panel.access_admin_dashboard`` antes de renderizar la
    plantilla.

    :param request: Objeto de la petición HTTP.
    :type request: :class:`django.http.HttpRequest`
    :returns: Si el usuario posee el permiso, renderiza ``admin_panel/dashboard.html``.
              En caso contrario, redirige a la página ``home``.
    :rtype: :class:`django.http.HttpResponse` | :class:`django.http.HttpResponseRedirect`

    **Permisos necesarios**

    - ``admin_panel.access_admin_dashboard``

    **Plantilla**

    - ``admin_panel/dashboard.html``

    """
    if not request.user.has_perm("admin_panel.access_admin_dashboard"):
        # Redirige si el usuario no tiene el permiso requerido.
        return redirect("home")

    return render(request, "admin_panel/dashboard.html")
