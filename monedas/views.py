# monedas/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Moneda
from .forms import MonedaForm



@login_required
def listar_monedas(request):
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    monedas = Moneda.objects.all()
    return render(request, "monedas/listar.html", {"monedas": monedas})


@login_required
def crear_moneda(request):
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
    if not request.user.has_perm("monedas.access_monedas_section"):
        return redirect("home")

    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        moneda.delete()
        messages.success(request, "Moneda eliminada correctamente.")
        return redirect("monedas:listar_monedas")
    return render(request, "monedas/eliminar.html", {"moneda": moneda})
