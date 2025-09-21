from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from .models import MedioAcreditacion
from .forms import MedioAcreditacionForm

def listar_medios_acreditacion(request: HttpRequest) -> HttpResponse:
    qs = MedioAcreditacion.objects.all().order_by("nombre")
    return render(request, "acreditaciones/listar_medios_acreditacion.html", {"medios": qs})

def agregar_medio_acreditacion(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = MedioAcreditacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Medio de acreditación agregado.")
            return redirect("acreditaciones:listar_medios")
    else:
        form = MedioAcreditacionForm()
    return render(request, "acreditaciones/form_medio_acreditacion.html", {"form": form, "accion": "Agregar"})

def editar_medio_acreditacion(request: HttpRequest, pk: int) -> HttpResponse:
    medio = get_object_or_404(MedioAcreditacion, pk=pk)
    if request.method == "POST":
        form = MedioAcreditacionForm(request.POST, instance=medio)
        if form.is_valid():
            form.save()
            messages.success(request, "Cambios guardados.")
            return redirect("acreditaciones:listar_medios")
    else:
        form = MedioAcreditacionForm(instance=medio)
    return render(request, "acreditaciones/form_medio_acreditacion.html", {"form": form, "accion": "Editar"})

def ver_medio_acreditacion(request: HttpRequest, pk: int) -> HttpResponse:
    medio = get_object_or_404(MedioAcreditacion, pk=pk)
    return render(request, "acreditaciones/ver_medio_acreditacion.html", {"medio": medio})

def eliminar_medio_acreditacion(request: HttpRequest, pk: int) -> HttpResponse:
    medio = get_object_or_404(MedioAcreditacion, pk=pk)
    if request.method == "POST":
        medio.delete()
        messages.success(request, "Medio de acreditación eliminado.")
        return redirect("acreditaciones:listar_medios")
    return render(request, "acreditaciones/confirmar_eliminacion.html", {"medio": medio})

def toggle_activo(request: HttpRequest, pk: int) -> HttpResponse:
    medio = get_object_or_404(MedioAcreditacion, pk=pk)
    if request.method == "POST":
        medio.activo = not medio.activo
        medio.save(update_fields=["activo", "updated_at"])
    return redirect("acreditaciones:listar_medios")
