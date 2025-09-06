# cotizaciones/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError

from .models import Cotizacion
from monedas.models import Moneda 
from .forms import CotizacionForm



@login_required
def cotizacion_list(request):
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
        return redirect("home")

    cotizaciones = Cotizacion.objects.all()
    return render(request, 'cotizaciones/cotizacion_list.html', {'cotizaciones': cotizaciones})


@login_required
def cotizacion_create(request):
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
        return redirect("home")

    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        if form.is_valid():
            try:
                # Fuerza la moneda base PYG
                moneda_base = Moneda.objects.get(codigo='PYG')
                # Verificar si ya existe la cotización
                if Cotizacion.objects.filter(
                    moneda_base=moneda_base,
                    moneda_destino=form.cleaned_data['moneda_destino']
                ).exists():
                    messages.error(request, "Ya existe una cotización para esta moneda destino.")
                else:
                    form.instance.moneda_base = moneda_base
                    form.save()
                    messages.success(request, "Cotización guardada correctamente.")
                    return redirect('cotizaciones:cotizacion_list')
            except Moneda.DoesNotExist:
                messages.error(request, "La moneda base Guaraní (PYG) no está registrada.")
    else:
        form = CotizacionForm()
    return render(request, 'cotizaciones/cotizacion_form.html', {'form': form})


@login_required
def cotizacion_update(request, pk):
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
        return redirect("home")

    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        form = CotizacionForm(request.POST, instance=cotizacion)
        if form.is_valid():
            form.save()
            messages.success(request, "Cotización actualizada correctamente.")
            return redirect('cotizaciones:cotizacion_list')
    else:
        form = CotizacionForm(instance=cotizacion)
    return render(request, 'cotizaciones/cotizacion_form.html', {'form': form})


@login_required
def cotizacion_delete(request, pk):
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
        return redirect("home")

    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        cotizacion.delete()
        messages.success(request, "Cotización eliminada correctamente.")
        return redirect('cotizaciones:cotizacion_list')
    return render(request, 'cotizaciones/cotizacion_confirm_delete.html', {'cotizacion': cotizacion})
