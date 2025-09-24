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
    extra=0,          # 👈 SIN fila vacía automática
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
        # en GET y en POST previo al guardado del padre, sin instance
        context["formset"] = CampoFormSet(self.request.POST or None, self.request.FILES or None)
        context["accion"] = "crear"
        return context

    def form_valid(self, form):
        # 1) Guardar el padre
        self.object = form.save()

        # 2) RECONSTRUIR el formset con instance=self.object y los mismos POST/FILES
        formset = CampoFormSet(self.request.POST, self.request.FILES, instance=self.object)

        # 3) Validar el formset ya sobre la instancia correcta
        if not formset.is_valid():
            messages.error(self.request, "Revisá los campos: hay errores en la definición de campos.")
            # Re-render con el formset rearmado (para mostrar errores)
            return self.render_to_response(self.get_context_data(form=form))

        # 4) Guardar (en crear podés eliminar realmente los marcados con DELETE)
        instances = formset.save(commit=False)
        for inst in instances:
            # por si acaso
            inst.tipo_medio = self.object
            inst.activo = True
            inst.save()

        # Borrar los marcados
        for obj in formset.deleted_objects:
            obj.delete()

        messages.success(self.request, "Tipo de medio y campos creados correctamente ✅")
        return redirect(self.success_url)

    
    

class TipoMedioUpdateView(UpdateView):
    model = TipoMedioAcreditacion
    form_class = TipoMedioForm
    template_name = "medios_acreditacion/tipos_form.html"
    success_url = reverse_lazy("medios_acreditacion:tipos_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = CampoFormSet(self.request.POST, instance=self.object)
        else:
            context["formset"] = CampoFormSet(instance=self.object)
        context["accion"] = "editar"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if not formset.is_valid():
            for idx, f in enumerate(formset.forms, start=1):
                if f.errors:
                    messages.error(self.request, f"Fila {idx}: {f.errors}")
            messages.error(self.request, "Revisá los campos: hay errores en la definición de campos.")
            return self.render_to_response(self.get_context_data(form=form))

        # Guardar primero el Tipo
        self.object = form.save()

        # 1) Crear/actualizar (sin borrar aún)
        instances = formset.save(commit=False)
        for inst in instances:
            inst.tipo_medio = self.object
            # si es nuevo, por defecto activo
            if inst.pk is None:
                inst.activo = True
            inst.save()

        # 2) Desactivar: los marcados como DELETE
        for obj in formset.deleted_objects:
            if obj.pk:
                obj.activo = False
                obj.save()

        # 3) **Reactivar**: formularios existentes que NO están en DELETE
        #    y cuya instancia actual está inactiva.
        for f in formset.forms:
            inst = f.instance
            if inst.pk:
                # Si el form tiene el campo DELETE (lo tiene en inline formset):
                marked_delete = f.cleaned_data.get('DELETE', False)
                if inst.activo is False and not marked_delete:
                    inst.activo = True
                    inst.save()

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
