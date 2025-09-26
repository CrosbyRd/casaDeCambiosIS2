"""
Vistas de la aplicación **configuracion**.

.. module:: configuracion.views
   :synopsis: Gestión de límites transaccionales de la plataforma.

Este módulo implementa vistas basadas en funciones para administrar los
**límites de transacciones**. Incluye las operaciones CRUD (crear, listar,
editar, eliminar), manejo de permisos y mensajes al usuario.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TransactionLimit
from .forms import TransactionLimitForm


def configuracion_panel(request):
    """
    Renderiza el panel principal de configuración.

    **Template**
    ------------
    - ``configuracion/configuracion_panel.html``

    **Parámetros**
    --------------
    request : HttpRequest
        La petición HTTP recibida.

    **Retorna**
    -----------
    HttpResponse
        Página HTML con el panel de configuración.
    """
    return render(request, "configuracion/configuracion_panel.html")

# Lista de límites
#@login_required
def lista_limites(request):
    """
    Lista todos los límites de transacciones configurados.

    **Restricciones**
    -----------------
    - (Opcional) Requiere el permiso ``configuracion.access_configuracion``.

    **Template**
    ------------
    - ``configuracion/lista_limites.html``

    **Contexto**
    ------------
    - ``limites`` : QuerySet con todos los objetos
      :class:`configuracion.models.TransactionLimit`.

    **Retorna**
    -----------
    HttpResponse
        Página HTML con el listado de límites.
    """
    # if not request.user.has_perm("configuracion.access_configuracion"):
    #     return redirect("home")  # Redirige si no tiene permiso
    limites = TransactionLimit.objects.all()
    return render(request, "configuracion/lista_limites.html", {"limites": limites})

# Crear límite
#@login_required
def crear_limite(request):
    """
    Crea un nuevo límite de transacciones.

    **Comportamiento**
    ------------------
    - Si el método es ``POST``:
        - Valida el formulario :class:`configuracion.forms.TransactionLimitForm`.
        - Asigna automáticamente la moneda base (PYG).
        - Guarda el objeto en la base de datos.
        - Redirige a la lista de límites con mensaje de éxito.
    - Si el método es ``GET``:
        - Muestra el formulario vacío.

    **Template**
    ------------
    - ``configuracion/editar_limite.html``

    **Contexto**
    ------------
    - ``form`` : instancia de TransactionLimitForm.

    **Retorna**
    -----------
    HttpResponse
        Página con el formulario de creación.
    """
    if request.method == "POST":
        form = TransactionLimitForm(request.POST)
        if form.is_valid():
            limite = form.save(commit=False)
            # Siempre usar la moneda base
            from monedas.models import Moneda
            limite.moneda = Moneda.objects.get(codigo='PYG')
            limite.save()
            messages.success(request, "Límite creado correctamente.")
            return redirect("configuracion:lista_limites")
    else:
        form = TransactionLimitForm()
    return render(request, "configuracion/editar_limite.html", {"form": form})


# Editar límite
#@login_required
def editar_limite(request, pk):
    """
    Edita un límite de transacciones existente.

    **Parámetros**
    --------------
    request : HttpRequest
        La petición HTTP recibida.
    pk : UUID | int
        Identificador primario del límite a editar.

    **Comportamiento**
    ------------------
    - Carga el objeto :class:`configuracion.models.TransactionLimit`.
    - Si el método es ``POST``:
        - Valida y guarda los cambios.
        - Asigna la moneda base (PYG).
        - Redirige con mensaje de éxito.
    - Si el método es ``GET``:
        - Muestra el formulario con datos iniciales.

    **Template**
    ------------
    - ``configuracion/editar_limite.html``

    **Contexto**
    ------------
    - ``form`` : instancia de TransactionLimitForm.

    **Retorna**
    -----------
    HttpResponse
        Página con el formulario de edición.
    """
    limite = get_object_or_404(TransactionLimit, pk=pk)
    if request.method == "POST":
        form = TransactionLimitForm(request.POST, instance=limite)
        if form.is_valid():
            limite = form.save(commit=False)
            # Siempre usar la moneda base
            from monedas.models import Moneda
            limite.moneda = Moneda.objects.get(codigo='PYG')
            limite.save()
            messages.success(request, "Límite actualizado correctamente.")
            return redirect("configuracion:lista_limites")
    else:
        form = TransactionLimitForm(instance=limite)
    return render(request, "configuracion/editar_limite.html", {"form": form})


# Eliminar límite
#@login_required
def eliminar_limite(request, pk):
    """
    Elimina un límite de transacciones.

    **Parámetros**
    --------------
    request : HttpRequest
        La petición HTTP recibida.
    pk : UUID | int
        Identificador primario del límite a eliminar.

    **Comportamiento**
    ------------------
    - Si el método es ``POST``:
        - Elimina el objeto.
        - Redirige a la lista de límites con mensaje de éxito.
    - Si el método es ``GET``:
        - Muestra la confirmación antes de eliminar.

    **Template**
    ------------
    - ``configuracion/eliminar_limite.html``

    **Contexto**
    ------------
    - ``limite`` : instancia de :class:`configuracion.models.TransactionLimit`.

    **Retorna**
    -----------
    HttpResponse
        Página de confirmación o redirección tras eliminar.
    """
    # if not request.user.has_perm("configuracion.access_configuracion"):
    #     return redirect("home")
    limite = get_object_or_404(TransactionLimit, pk=pk)
    if request.method == "POST":
        limite.delete()
        messages.success(request, "Límite eliminado correctamente.")
        return redirect("configuracion:lista_limites")
    return render(request, "configuracion/eliminar_limite.html", {"limite": limite})
