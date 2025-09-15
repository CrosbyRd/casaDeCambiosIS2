"""
==================================
Módulo views de la app monedas
==================================

Este módulo contiene las vistas de la aplicación ``monedas``.  
Permite realizar operaciones CRUD sobre el modelo :class:`Moneda`, 
con validación de permisos y protección mediante autenticación.

Contenido
---------
- Vistas basadas en funciones protegidas con ``@login_required``.
- Gestión de formularios mediante :class:`MonedaForm`.
- Uso de mensajes de retroalimentación al usuario.

Funciones
---------
- :func:`listar_monedas`: Lista todas las monedas.
- :func:`crear_moneda`: Permite crear una nueva moneda.
- :func:`editar_moneda`: Permite editar una moneda existente.
- :func:`eliminar_moneda`: Elimina una moneda seleccionada.
- :func:`moneda_detalle`: Muestra el detalle de una moneda específica.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Moneda
from .forms import MonedaForm


@login_required
def listar_monedas(request):
    """
    Vista para listar todas las monedas registradas en el sistema.

    :param request: Objeto HttpRequest con los datos de la solicitud.
    :type request: HttpRequest
    :return: Respuesta renderizada con la plantilla ``monedas/listar.html``.
    :rtype: HttpResponse
    """
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    monedas = Moneda.objects.all()
    return render(request, "monedas/listar.html", {"monedas": monedas})


@login_required
def crear_moneda(request):
    """
    Vista para crear una nueva moneda en el sistema.

    - Si el método es ``POST`` y el formulario es válido, guarda la moneda.
    - Muestra un formulario vacío en caso contrario.

    :param request: Objeto HttpRequest con los datos de la solicitud.
    :type request: HttpRequest
    :return: Respuesta renderizada con la plantilla ``monedas/crear.html``.
    :rtype: HttpResponse
    """
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    if request.method == "POST":
        form = MonedaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Moneda creada correctamente.")
            return redirect("monedas:listar_monedas")
    else:
        form = MonedaForm()
    return render(request, "monedas/crear.html", {"form": form})


@login_required
def editar_moneda(request, pk):
    """
    Vista para editar una moneda existente.

    - Recupera la moneda por ``pk``.
    - Si el formulario es válido, actualiza la moneda en la base de datos.

    :param request: Objeto HttpRequest con los datos de la solicitud.
    :type request: HttpRequest
    :param pk: Identificador primario de la moneda a editar.
    :type pk: int
    :return: Respuesta renderizada con la plantilla ``monedas/editar.html``.
    :rtype: HttpResponse
    """
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        form = MonedaForm(request.POST, instance=moneda)
        if form.is_valid():
            form.save()
            messages.success(request, "Moneda actualizada correctamente.")
            return redirect("monedas:listar_monedas")
    else:
        form = MonedaForm(instance=moneda)
    return render(request, "monedas/editar.html", {"form": form, "moneda": moneda})


@login_required
def eliminar_moneda(request, pk):
    """
    Vista para eliminar una moneda existente.

    - Recupera la moneda por ``pk``.
    - Si el método es ``POST``, elimina la moneda y redirige al listado.

    :param request: Objeto HttpRequest con los datos de la solicitud.
    :type request: HttpRequest
    :param pk: Identificador primario de la moneda a eliminar.
    :type pk: int
    :return: Respuesta renderizada con la plantilla ``monedas/eliminar.html``.
    :rtype: HttpResponse
    """
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        moneda.delete()
        messages.success(request, "Moneda eliminada correctamente.")
        return redirect("monedas:listar_monedas")
    return render(request, "monedas/eliminar.html", {"moneda": moneda})


@login_required
def moneda_detalle(request, pk):
    """
    Vista para mostrar el detalle de una moneda.

    :param request: Objeto HttpRequest con los datos de la solicitud.
    :type request: HttpRequest
    :param pk: Identificador primario de la moneda a consultar.
    :type pk: int
    :return: Respuesta renderizada con la plantilla ``monedas/moneda_detalle.html``.
    :rtype: HttpResponse
    """
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    moneda = get_object_or_404(Moneda, pk=pk)
    return render(request, "monedas/moneda_detalle.html", {"moneda": moneda})
