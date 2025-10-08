from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.forms import inlineformset_factory
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View

from .models import TipoMedioPago, CampoMedioPago, MedioPagoCliente
from .forms import TipoMedioPagoForm, CampoMedioPagoForm, MedioPagoClienteForm

# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class AccessPagosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "pagos.access_pagos_section"
    raise_exception = False

    def handle_no_permission(self):
        messages.warning(self.request, "No tenés permisos para acceder a Pagos.")
        return redirect("home")

class RequireClienteMixin(LoginRequiredMixin):
    """Obtiene el cliente asociado al usuario (ajusta a tu modelo)."""
    def get_cliente(self):
        # Asumiendo relación M2M: user.clientes; ajusta a tu modelo real
        user = self.request.user
        cliente = getattr(user, "clientes", None)
        if cliente:
            cliente = cliente.first()
        if not cliente:
            messages.error(self.request, "No se encontró un cliente asociado.")
            redirect_url = reverse_lazy("home")
            raise Exception(f"Cliente requerido. Redirigir a {redirect_url}")
        return cliente

# ---------------------------------------------------------------------------
# Admin – Tipos de medios de pago
# ---------------------------------------------------------------------------
CampoFormSet = inlineformset_factory(
    parent_model=TipoMedioPago,
    model=CampoMedioPago,
    form=CampoMedioPagoForm,
    extra=0,
    can_delete=True,
)

class TipoPagoListView(AccessPagosMixin, ListView):
    model = TipoMedioPago
    template_name = "pagos/tipos_list.html"
    context_object_name = "tipos"

    def get_queryset(self):
        qs = super().get_queryset().order_by("-activo", "nombre")
        # Anotar si está en uso para bloquear borrado en el template
        return qs

class TipoPagoCreateView(AccessPagosMixin, CreateView):
    model = TipoMedioPago
    form_class = TipoMedioPagoForm
    template_name = "pagos/tipos_form.html"
    success_url = reverse_lazy("pagos:tipos_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = CampoFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = CampoFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            # Nuevos campos -> activo True por defecto
            campos = formset.save(commit=False)
            for c in campos:
                c.tipo = self.object
                if c.pk is None:
                    c.activo = True
                c.save()
            for c in formset.deleted_objects:
                # En creación sí permitimos borrar del formset (no hay referencias todavía)
                c.delete()
            messages.success(self.request, "Tipo de medio de pago creado correctamente.")
            return redirect(self.get_success_url())
        messages.error(self.request, "Revisá los errores del formulario.")
        return self.form_invalid(form)

class TipoPagoUpdateView(AccessPagosMixin, UpdateView):
    model = TipoMedioPago
    form_class = TipoMedioPagoForm
    template_name = "pagos/tipos_form.html"
    success_url = reverse_lazy("pagos:tipos_list")
    pk_url_kwarg = "id_tipo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = CampoFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = CampoFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            campos = formset.save(commit=False)
            # Regla: marcado como DELETE -> desactivar, no borrar
            for c in formset.deleted_objects:
                c.activo = False
                c.save(update_fields=["activo"])
            for c in campos:
                c.tipo = self.object
                # Si vuelve a aparecer en el form sin DELETE, lo reactivamos
                if c.pk and c.activo is False:
                    c.activo = True
                c.save()
            messages.success(self.request, "Tipo de medio de pago actualizado correctamente.")
            return redirect(self.get_success_url())
        messages.error(self.request, "Revisá los errores del formulario.")
        return self.form_invalid(form)

class TipoPagoDeleteView(AccessPagosMixin, DeleteView):
    model = TipoMedioPago
    template_name = "pagos/tipos_confirm_delete.html"
    success_url = reverse_lazy("pagos:tipos_list")
    pk_url_kwarg = "id_tipo"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Bloquear si está en uso por algún cliente
        if self.object.medios_cliente.exists():
            messages.error(request, "No se puede eliminar: hay medios de pago de clientes usando este tipo.")
            return redirect(self.success_url)
        messages.success(request, "Tipo de medio de pago eliminado.")
        return super().delete(request, *args, **kwargs)

# ---------------------------------------------------------------------------
# Cliente – Medios de pago
# ---------------------------------------------------------------------------
class MedioPagoListView(RequireClienteMixin, ListView):
    model = MedioPagoCliente
    template_name = "pagos/clientes_list.html"
    context_object_name = "medios"

    def get_queryset(self):
        cliente = self.get_cliente()
        return (
            MedioPagoCliente.objects.select_related("tipo")
            .filter(cliente=cliente)
            .order_by("-activo", "-predeterminado", "alias")
        )

class MedioPagoCreateView(RequireClienteMixin, CreateView):
    model = MedioPagoCliente
    form_class = MedioPagoClienteForm
    template_name = "pagos/clientes_form.html"
    success_url = reverse_lazy("pagos:clientes_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        if self.request.method == "GET" and self.request.GET.get("tipo"):
            kwargs.setdefault("initial", {})["tipo"] = self.request.GET.get("tipo")
        return kwargs


    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.cliente = self.get_cliente()
        obj.save()
        messages.success(self.request, "Medio de pago creado correctamente.")
        return redirect(self.success_url)


class MedioPagoUpdateView(RequireClienteMixin, UpdateView):
    model = MedioPagoCliente
    form_class = MedioPagoClienteForm
    template_name = "pagos/clientes_form.html"
    success_url = reverse_lazy("pagos:clientes_list")
    pk_url_kwarg = "id_medio"

    def get_queryset(self):
        return MedioPagoCliente.objects.filter(cliente=self.get_cliente())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Medio de pago actualizado correctamente.")
        return super().form_valid(form)

class MedioPagoDeleteView(RequireClienteMixin, DeleteView):
    model = MedioPagoCliente
    template_name = "pagos/clientes_confirm_delete.html"
    success_url = reverse_lazy("pagos:clientes_list")
    pk_url_kwarg = "id_medio"

    def get_queryset(self):
        return MedioPagoCliente.objects.filter(cliente=self.get_cliente())

class MedioPagoPredeterminarView(RequireClienteMixin, View):
    def post(self, request, *args, **kwargs):
        cliente = self.get_cliente()
        try:
            medio = MedioPagoCliente.objects.get(pk=kwargs.get("id_medio"), cliente=cliente, activo=True)
        except MedioPagoCliente.DoesNotExist:
            return HttpResponseForbidden("No permitido")
        medio.predeterminado = True
        medio.save(update_fields=["predeterminado", "actualizado_en"])
        return HttpResponse(status=204)

    def get(self, *args, **kwargs):
        return HttpResponseForbidden("Método no permitido")