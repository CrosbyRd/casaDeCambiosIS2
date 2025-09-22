# medios_acreditacion/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from .models import CategoriaMedio
from .forms import CategoriaMedioForm

def listar_categorias(request: HttpRequest) -> HttpResponse:
    categorias = CategoriaMedio.objects.all()
    return render(request, "medios_acreditacion/listar.html", {"categorias": categorias})

def agregar_categoria(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CategoriaMedioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("medios_acreditacion:listar_categorias")
    else:
        form = CategoriaMedioForm()
    return render(request, "medios_acreditacion/form.html", {"form": form, "accion": "Agregar"})

def editar_categoria(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaMedio, pk=pk)
    if request.method == "POST":
        form = CategoriaMedioForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect("medios_acreditacion:listar_categorias")
    else:
        form = CategoriaMedioForm(instance=categoria)
    return render(request, "medios_acreditacion/form.html", {"form": form, "accion": "Editar"})

def eliminar_categoria(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaMedio, pk=pk)
    if request.method == "POST":
        categoria.delete()
        return redirect("medios_acreditacion:listar_categorias")
    return render(request, "medios_acreditacion/confirmar_eliminacion.html", {"categoria": categoria})

def toggle_activo(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaMedio, pk=pk)
    if request.method == "POST":
        categoria.activo = not categoria.activo
        categoria.save(update_fields=["activo", "ultima_modificacion"])
    return redirect("medios_acreditacion:listar_categorias")

def ver_categoria(request: HttpRequest, pk: int) -> HttpResponse:
    categoria = get_object_or_404(CategoriaMedio, pk=pk)
    return render(request, "medios_acreditacion/ver.html", {"categoria": categoria})
