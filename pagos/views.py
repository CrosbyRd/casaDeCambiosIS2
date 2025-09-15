"""Vistas de la aplicación *pagos*.

Este módulo implementa vistas basadas en funciones (FBV) para administrar
instancias de :class:`pagos.models.TipoMedioPago`. Las vistas renderizan
templates HTML y usan el formulario :class:`pagos.forms.TipoMedioPagoForm`.

Templates utilizados:

- ``pagos/listar_tipos_medio_pago.html``
- ``pagos/form_tipo_medio_pago.html``
- ``pagos/confirmar_eliminacion.html``
- ``pagos/ver_tipo_medio_pago.html``
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required  # noqa: F401 (reservado por si se protege el acceso)
from django.http import HttpRequest, HttpResponse
from .models import TipoMedioPago
from .forms import TipoMedioPagoForm


def listar_tipos_medio_pago(request: HttpRequest) -> HttpResponse:
    """Lista todos los **tipos de medio de pago** ordenados por nombre.

    :param request: Objeto :class:`django.http.HttpRequest` de la petición.
    :returns: Respuesta HTML con el template
              ``pagos/listar_tipos_medio_pago.html`` y el contexto ``{"tipos": QuerySet}``.
    """
    tipos = TipoMedioPago.objects.all().order_by("nombre")
    return render(request, "pagos/listar_tipos_medio_pago.html", {"tipos": tipos})


def agregar_tipo_medio_pago(request: HttpRequest) -> HttpResponse:
    """Crea un nuevo :class:`pagos.models.TipoMedioPago`.

    - **GET**: Renderiza el formulario vacío.
    - **POST**: Valida y guarda, luego redirige al listado.

    :param request: Objeto :class:`django.http.HttpRequest`.
    :returns: Respuesta HTML con ``pagos/form_tipo_medio_pago.html`` o
              redirección a ``pagos:listar_tipos_medio_pago``.
    """
    if request.method == "POST":
        form = TipoMedioPagoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("pagos:listar_tipos_medio_pago")
    else:
        form = TipoMedioPagoForm()
    return render(request, "pagos/form_tipo_medio_pago.html", {"form": form, "accion": "Agregar"})


def editar_tipo_medio_pago(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita un :class:`pagos.models.TipoMedioPago` existente.

    - **GET**: Renderiza el formulario con la instancia.
    - **POST**: Valida y guarda cambios, luego redirige al listado.

    :param request: Objeto :class:`django.http.HttpRequest`.
    :param pk: Clave primaria del registro a editar.
    :returns: Respuesta HTML con ``pagos/form_tipo_medio_pago.html`` o
              redirección a ``pagos:listar_tipos_medio_pago``.
    :raises Http404: Si no existe un objeto con la ``pk`` indicada.
    """
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    if request.method == "POST":
        form = TipoMedioPagoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            return redirect("pagos:listar_tipos_medio_pago")
    else:
        form = TipoMedioPagoForm(instance=tipo)
    return render(request, "pagos/form_tipo_medio_pago.html", {"form": form, "accion": "Editar"})


def eliminar_tipo_medio_pago(request: HttpRequest, pk: int) -> HttpResponse:
    """Elimina un :class:`pagos.models.TipoMedioPago` previa confirmación.

    - **GET**: Muestra la página de confirmación.
    - **POST**: Elimina y redirige al listado.

    :param request: Objeto :class:`django.http.HttpRequest`.
    :param pk: Clave primaria del registro a eliminar.
    :returns: Respuesta HTML con ``pagos/confirmar_eliminacion.html`` o
              redirección a ``pagos:listar_tipos_medio_pago``.
    :raises Http404: Si no existe un objeto con la ``pk`` indicada.
    """
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    if request.method == "POST":
        tipo.delete()
        return redirect("pagos:listar_tipos_medio_pago")
    return render(request, "pagos/confirmar_eliminacion.html", {"tipo": tipo})


# --- Vistas adicionales ---


def ver_tipo_medio_pago(request: HttpRequest, pk: int) -> HttpResponse:
    """Muestra el **detalle** de un :class:`pagos.models.TipoMedioPago`.

    :param request: Objeto :class:`django.http.HttpRequest`.
    :param pk: Clave primaria del registro a visualizar.
    :returns: Respuesta HTML con el template ``pagos/ver_tipo_medio_pago.html`` y
              el contexto ``{"tipo": TipoMedioPago}``.
    :raises Http404: Si no existe un objeto con la ``pk`` indicada.
    """
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    return render(request, "pagos/ver_tipo_medio_pago.html", {"tipo": tipo})


def toggle_activo_tipo_medio_pago(request: HttpRequest, pk: int) -> HttpResponse:
    """Alterna el estado ``activo`` de un :class:`pagos.models.TipoMedioPago`.

    Esta vista se invoca típicamente mediante un botón de acción. Por seguridad,
    el cambio de estado se efectúa únicamente mediante **POST** y luego se
    redirige al listado.

    :param request: Objeto :class:`django.http.HttpRequest`.
    :param pk: Clave primaria del registro cuyo estado se alternará.
    :returns: Redirección a ``pagos:listar_tipos_medio_pago``.
    :raises Http404: Si no existe un objeto con la ``pk`` indicada.
    """
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    if request.method == "POST":
        tipo.activo = not tipo.activo
        tipo.save(update_fields=["activo", "updated_at"])
    return redirect("pagos:listar_tipos_medio_pago")
