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
# (UN SOLO FORMSET para crear y editar; siempre con can_delete=True)
# =====================================================
CampoFormSet = inlineformset_factory(
    parent_model=TipoMedioAcreditacion,
    model=CampoMedioAcreditacion,
    form=CampoMedioForm,
    extra=0,
    can_delete=True,
)

# =====================================================
# VISTAS PARA TIPOS DE MEDIO (admin)
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
        context["formset"] = CampoFormSet(self.request.POST or None, self.request.FILES or None)
        context["accion"] = "crear"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            messages.error(self.request, "Revisá los campos: hay errores en la definición de campos.")
            return self.render_to_response(self.get_context_data(form=form))

        # Guardar Tipo primero
        self.object = form.save()
        formset.instance = self.object

        # En creación, dejamos que Django borre realmente lo marcado (o ignore si eran nuevos)
        formset.save()

        messages.success(self.request, "Tipo de medio y campos creados correctamente ✅")
        return redirect(self.success_url)


class TipoMedioUpdateView(UpdateView):
    model = TipoMedioAcreditacion
    form_class = TipoMedioForm
    template_name = "medios_acreditacion/tipos_form.html"
    success_url = reverse_lazy("medios_acreditacion:tipos_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formset"] = CampoFormSet(
            self.request.POST or None,
            self.request.FILES or None,
            instance=self.object,
        )
        context["accion"] = "editar"
        return context

    def form_valid(self, form):
        """
        Opción rápida: si en la edición marcan DELETE en una fila,
        NO la borramos: la marcamos como inactiva (activo=False).
        El resto se guarda normal.
        """
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            messages.error(self.request, "Revisá los campos: hay errores en la definición de campos.")
            return self.render_to_response(self.get_context_data(form=form))

        # Guardar Tipo primero
        self.object = form.save()
        formset.instance = self.object

        # Guardar / crear cambios sin aplicar deletes todavía
        instances = formset.save(commit=False)

        # 1) Desactivar los que vinieron marcados para borrar
        #    (si no tienen pk, eran nuevos en la vista y no llegaron a BD: se ignoran)
        for obj in formset.deleted_objects:
            if obj.pk:
                obj.activo = False
                obj.save()

        # 2) Guardar/crear los demás normalmente (nuevo activo=True por default del modelo)
        for inst in instances:
            # Por si acaso, aseguramos el FK
            inst.tipo_medio = self.object
            inst.save()

        # 3) Relaciones many-to-many si existieran (no aplica acá, pero es seguro)
        formset.save_m2m()

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
