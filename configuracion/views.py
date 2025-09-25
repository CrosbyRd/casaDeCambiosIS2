from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TransactionLimit
from .forms import TransactionLimitForm


def configuracion_panel(request):
    return render(request, "configuracion/configuracion_panel.html")

# Lista de límites
#@login_required
def lista_limites(request):
    # if not request.user.has_perm("configuracion.access_configuracion"):
    #     return redirect("home")  # Redirige si no tiene permiso
    limites = TransactionLimit.objects.all()
    return render(request, "configuracion/lista_limites.html", {"limites": limites})

# Crear límite
#@login_required
def crear_limite(request):
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
    # if not request.user.has_perm("configuracion.access_configuracion"):
    #     return redirect("home")
    limite = get_object_or_404(TransactionLimit, pk=pk)
    if request.method == "POST":
        limite.delete()
        messages.success(request, "Límite eliminado correctamente.")
        return redirect("configuracion:lista_limites")
    return render(request, "configuracion/eliminar_limite.html", {"limite": limite})
