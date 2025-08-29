from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Moneda
from .forms import MonedaForm

@login_required(login_url="/cuentas/login/")
def listar_monedas(request):
    monedas = Moneda.objects.all()
    return render(request, "monedas/listar.html", {"monedas": monedas})

@login_required(login_url="/cuentas/login/")
def crear_moneda(request):
    if request.method == "POST":
        form = MonedaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("monedas:listar_monedas")
    else:
        form = MonedaForm()
    return render(request, "monedas/crear.html", {"form": form})

@login_required(login_url="/cuentas/login/")
def editar_moneda(request, pk):
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        form = MonedaForm(request.POST, instance=moneda)
        if form.is_valid():
            form.save()
            return redirect("monedas:listar_monedas")
    else:
        form = MonedaForm(instance=moneda)
    return render(request, "monedas/editar.html", {"form": form, "moneda": moneda})

@login_required(login_url="/cuentas/login/")
def eliminar_moneda(request, pk):
    moneda = get_object_or_404(Moneda, pk=pk)
    if request.method == "POST":
        moneda.delete()
        return redirect("monedas:listar_monedas")
    return render(request, "monedas/eliminar.html", {"moneda": moneda})
