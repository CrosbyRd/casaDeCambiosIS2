from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Cotizacion
from .forms import CotizacionForm
from monedas.models import Moneda


@login_required
def cotizacion_list(request):
    qs = Cotizacion.objects.select_related("moneda_base", "moneda_destino") \
                           .order_by("moneda_base__codigo", "moneda_destino__codigo")
    return render(request, "cotizaciones/cotizacion_list.html", {"cotizaciones": qs})


@login_required
def cotizacion_create(request):
    if request.method == "POST":
        form = CotizacionForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # Aseguramos que exista la base PYG y la asignamos
            base, _ = Moneda.objects.get_or_create(
                codigo="PYG",
                defaults={"nombre": "Guaraní paraguayo"}
            )
            obj.moneda_base = base
            obj.save()
            messages.success(request, "Cotización creada correctamente.")
            return redirect("cotizaciones:cotizacion_list")
    else:
        form = CotizacionForm()
    return render(request, "cotizaciones/cotizacion_form.html", {"form": form})


@login_required
def cotizacion_update(request, pk):
    obj = get_object_or_404(Cotizacion, pk=pk)
    if request.method == "POST":
        form = CotizacionForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            # Mantenemos base en PYG
            base = Moneda.objects.filter(codigo="PYG").first()
            if base:
                obj.moneda_base = base
            obj.save()
            messages.success(request, "Cotización actualizada.")
            return redirect("cotizaciones:cotizacion_list")
    else:
        form = CotizacionForm(instance=obj)
    return render(request, "cotizaciones/cotizacion_form.html", {"form": form, "object": obj})


@login_required
def cotizacion_delete(request, pk):
    obj = get_object_or_404(Cotizacion, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Cotización eliminada.")
        return redirect("cotizaciones:cotizacion_list")
    return render(request, "cotizaciones/cotizacion_confirm_delete.html", {"object": obj})
