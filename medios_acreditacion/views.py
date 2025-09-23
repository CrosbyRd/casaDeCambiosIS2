from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.forms import inlineformset_factory
from django.shortcuts import redirect

from .models import (
    TipoMedioAcreditacion,
    CampoMedioAcreditacion,
    MedioAcreditacionCliente,
)
from .forms import (
    TipoMedioForm,
    CampoMedioForm,
    MedioAcreditacionClienteForm,
)

# =====================================================
# Formset inline: Campos dentro de un Tipo de Medio
# =====================================================
CampoFormSet = inlineformset_factory(
    parent_model=TipoMedioAcreditacion,
    model=CampoMedioAcreditacion,
    form=CampoMedioForm,
    extra=1,
    can_delete=True
)

# =====================================================
# VISTAS PARA TIPOS DE MEDIO (admin) — unificado con campos
# =====================================================
class TipoMedioListView(ListView):
    model = TipoMedioAcreditacion
    template_name = "medios_acreditacion/tipos_list.html"
    context_object_name = "tipos"


class TipoMedioCreateView(CreateView):
    model = TipoMedioAcreditacion
    form_class = TipoMedioForm
    template_name = "medios_acreditacion/tipos_form.html"
    success_url = reverse_lazy("medios_acreditacion:tipos_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context["formset"] = CampoFormSet(self.request.POST, self.request.FILES)
        else:
            context["formset"] = CampoFormSet()
        context["accion"] = "crear"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            messages.error(self.request, "Revisá los campos: hay errores en la definición de campos.")
            return self.render_to_response(self.get_context_data(form=form))

        self.object = form.save()
        formset.instance = self.object

        # Depuración: ver si DELETE llega
        for f in formset.forms:
            if f.is_valid():
                print(f.cleaned_data)

        formset.save(commit=True)

        messages.success(self.request, "Tipo de medio y campos creados correctamente ✅")
        return redirect(self.success_url)


class TipoMedioUpdateView(UpdateView):
    model = TipoMedioAcreditacion
    form_class = TipoMedioForm
    template_name = "medios_acreditacion/tipos_form.html"
    success_url = reverse_lazy("medios_acreditacion:tipos_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context["formset"] = CampoFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context["formset"] = CampoFormSet(instance=self.object)
        context["accion"] = "editar"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            messages.error(self.request, "Revisá los campos: hay errores en la definición de campos.")
            return self.render_to_response(self.get_context_data(form=form))

        self.object = form.save()
        formset.instance = self.object

        # Depuración: ver si DELETE llega
        for f in formset.forms:
            if f.is_valid():
                print(f.cleaned_data)

        formset.save(commit=True)

        messages.success(self.request, "Tipo de medio y campos actualizados correctamente ✏️")
        return redirect(self.success_url)


class TipoMedioDeleteView(DeleteView):
    model = TipoMedioAcreditacion
    template_name = "medios_acreditacion/tipos_confirm_delete.html"
    success_url = reverse_lazy("medios_acreditacion:tipos_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tipo de medio eliminado correctamente ❌")
        return super().delete(request, *args, **kwargs)

# =====================================================
# VISTAS PARA MEDIOS DE CLIENTES
# =====================================================
class MedioClienteListView(ListView):
    model = MedioAcreditacionCliente
    template_name = "medios_acreditacion/clientes_list.html"
    context_object_name = "medios"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(cliente__id_cliente=self.request.user.cliente.id_cliente)
        return qs


class MedioClienteCreateView(CreateView):
    model = MedioAcreditacionCliente
    form_class = MedioAcreditacionClienteForm
    template_name = "medios_acreditacion/clientes_form.html"
    success_url = reverse_lazy("medios_acreditacion:clientes_list")

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            form.instance.cliente = self.request.user.cliente
        messages.success(self.request, "Medio de acreditación agregado correctamente ✅")
        return super().form_valid(form)


class MedioClienteUpdateView(UpdateView):
    model = MedioAcreditacionCliente
    form_class = MedioAcreditacionClienteForm
    template_name = "medios_acreditacion/clientes_form.html"
    success_url = reverse_lazy("medios_acreditacion:clientes_list")

    def form_valid(self, form):
        messages.success(self.request, "Medio de acreditación actualizado correctamente ✏️")
        return super().form_valid(form)


class MedioClienteDeleteView(DeleteView):
    model = MedioAcreditacionCliente
    template_name = "medios_acreditacion/clientes_confirm_delete.html"
    success_url = reverse_lazy("medios_acreditacion:clientes_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Medio de acreditación eliminado correctamente ❌")
        return super().delete(request, *args, **kwargs)
