from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import TipoMedioPago
from .forms import TipoMedioPagoForm

def listar_tipos_medio_pago(request):
    tipos = TipoMedioPago.objects.all().order_by('nombre')
    return render(request, "pagos/listar_tipos_medio_pago.html", {"tipos": tipos})

def agregar_tipo_medio_pago(request):
    if request.method == 'POST':
        form = TipoMedioPagoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('pagos:listar_tipos_medio_pago')
    else:
        form = TipoMedioPagoForm()
    return render(request, "pagos/form_tipo_medio_pago.html", {"form": form, "accion": "Agregar"})

def editar_tipo_medio_pago(request, pk):
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    if request.method == 'POST':
        form = TipoMedioPagoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            return redirect('pagos:listar_tipos_medio_pago')
    else:
        form = TipoMedioPagoForm(instance=tipo)
    return render(request, "pagos/form_tipo_medio_pago.html", {"form": form, "accion": "Editar"})

def eliminar_tipo_medio_pago(request, pk):
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    if request.method == 'POST':
        tipo.delete()
        return redirect('pagos:listar_tipos_medio_pago')
    return render(request, "pagos/confirmar_eliminacion.html", {"tipo": tipo})

# --- NUEVOS ---

def ver_tipo_medio_pago(request, pk):
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    return render(request, "pagos/ver_tipo_medio_pago.html", {"tipo": tipo})

def toggle_activo_tipo_medio_pago(request, pk):
    tipo = get_object_or_404(TipoMedioPago, pk=pk)
    if request.method == 'POST':
        tipo.activo = not tipo.activo
        tipo.save(update_fields=['activo', 'updated_at'])
    return redirect('pagos:listar_tipos_medio_pago')
