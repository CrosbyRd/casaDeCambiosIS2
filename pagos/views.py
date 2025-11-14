"""


Vistas del módulo Pagos: manejo de tipos de medios de pago (administración) y
medios de pago del cliente (front-end de usuario).

.. module:: pagos.views
   :synopsis: Vistas de Django para la aplicación de pagos.

.. note::

   - Las vistas usan mixins de seguridad:
       - `LoginRequiredMixin` y `PermissionRequiredMixin` para administración.
       - `RequireClienteMixin` para acceso de clientes.

   - Las vistas de administración soportan **formsets dinámicos** para campos de medios
     de pago (excepto cuando el engine es Stripe, donde los campos se omiten).

"""
from django.contrib import messages
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.db.models import Count, Q
from django.template.loader import render_to_string # Importar para renderizar plantillas a string
from .models import TipoMedioPago, CampoMedioPago, MedioPagoCliente
from .forms import (
    TipoMedioPagoForm,
    CampoMedioPagoForm,          # (lo podés dejar si lo usás en admin)
    MedioPagoClienteForm,
    CampoMedioPagoFormSet,       # 👈 IMPORTANTE: usamos el formset correcto
)
from django.db import transaction
from django.utils.timezone import now
from django.urls import reverse
from usuarios.mixins import RequireClienteMixin
from clientes.models import Cliente # Importar Cliente para get_cliente_activo
from usuarios.utils import get_cliente_activo # Importar get_cliente_activo

# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class AccessPagosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "pagos.access_pagos_section"
    raise_exception = False

    def handle_no_permission(self):
        return redirect("home")

# ---------------------------------------------------------------------------
# Admin – Tipos de medios de pago
# ---------------------------------------------------------------------------
# ❌ ELIMINADO: el formset local creado con inlineformset_factory
# CampoFormSet = inlineformset_factory(...)

class TipoPagoListView(AccessPagosMixin, ListView):
    model = TipoMedioPago
    template_name = "pagos/tipos_list.html"
    context_object_name = "tipos"

    def get_queryset(self):
        # en_uso = cantidad de medios de clientes que usan este tipo (activos o no, a tu gusto)
        return (
            super()
            .get_queryset()
            .annotate(en_uso=Count("medios_cliente", distinct=True))  # <- usa tu related_name
            .order_by("-activo", "nombre")
        )

class TipoPagoCreateView(AccessPagosMixin, CreateView):
    model = TipoMedioPago
    form_class = TipoMedioPagoForm
    template_name = "pagos/tipos_form.html"
    success_url = reverse_lazy("pagos:tipos_list")

    def get_context_data(self, **kwargs):
            ctx = super().get_context_data(**kwargs)
            # Determinar engine desde POST o instancia
            current_engine = self.request.POST.get("engine") if self.request.method == "POST" else getattr(self.object, "engine", None)
            ctx["skip_formset"] = (current_engine == "stripe")
            if not ctx["skip_formset"]:
                ctx["formset"] = CampoMedioPagoFormSet(self.request.POST or None, instance=self.object)
            else:
                ctx["formset"] = None
            return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        skip = ctx.get("skip_formset", False)
        if not skip:
            formset = ctx["formset"]
            if form.is_valid() and formset.is_valid():
                self.object = form.save()
                campos = formset.save(commit=False)
                for c in campos:
                    c.tipo = self.object
                    if c.pk is None:
                        c.activo = True
                    c.save()
                for c in formset.deleted_objects:
                    c.delete()
                messages.success(self.request, "Tipo de medio de pago creado correctamente.")
                return redirect(self.get_success_url())
            messages.error(self.request, "Revisá los errores del formulario.")
            return self.form_invalid(form)

        # Engine Stripe: guardar sin formset
        self.object = form.save()
        messages.success(self.request, "Tipo de medio de pago (Stripe) creado correctamente.")
        return redirect(self.get_success_url())


class TipoPagoUpdateView(AccessPagosMixin, UpdateView):
    model = TipoMedioPago
    form_class = TipoMedioPagoForm
    template_name = "pagos/tipos_form.html"
    success_url = reverse_lazy("pagos:tipos_list")
    pk_url_kwarg = "id_tipo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        current_engine = self.request.POST.get("engine") if self.request.method == "POST" else getattr(self.object, "engine", None)
        ctx["skip_formset"] = (current_engine == "stripe")
        if not ctx["skip_formset"]:
            ctx["formset"] = CampoMedioPagoFormSet(self.request.POST or None, instance=self.object)
        else:
            ctx["formset"] = None
        return ctx
    
    def form_valid(self, form):
        ctx = self.get_context_data()
        skip = ctx.get("skip_formset", False)
        if not skip:
            formset = ctx["formset"]
            if form.is_valid() and formset.is_valid():
                self.object = form.save()
                campos = formset.save(commit=False)
                # DELETE => desactivar
                for c in formset.deleted_objects:
                    c.activo = False
                    c.save(update_fields=["activo"])
                for c in campos:
                    c.tipo = self.object
                    if c.pk and c.activo is False:
                        c.activo = True
                    c.save()
                messages.success(self.request, "Tipo de medio de pago actualizado correctamente.")
                return redirect(self.get_success_url())
            messages.error(self.request, "Revisá los errores del formulario.")
            return self.form_invalid(form)

    # Engine Stripe: guardar y desactivar cualquier campo que haya quedado
        self.object = form.save()
        self.object.campos.update(activo=False)
        messages.success(self.request, "Tipo (Stripe) actualizado. Los campos fueron desactivados.")
        return redirect(self.get_success_url())

class TipoPagoDeleteView(AccessPagosMixin, DeleteView):
    model = TipoMedioPago
    template_name = "pagos/tipos_confirm_delete.html"
    success_url = reverse_lazy("pagos:tipos_list")
    pk_url_kwarg = "id_tipo"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Bloquear si está en uso por al menos un cliente
        if self.object.medios_cliente.exists():   # <- usa tu related_name
            messages.warning(
                request,
                "No se puede eliminar este método: está siendo utilizado por clientes. "
                "Desactívalo si no querés que se use."
            )
            return redirect(self.success_url)

        messages.success(request, "Método de pago eliminado.")
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        # En lugar de mostrar una página de confirmación, redirigimos a la lista
        messages.info(request, "Usá el botón Eliminar para confirmar desde el listado.")
        return redirect(self.success_url)
# ---------------------------------------------------------------------------
# Cliente – Medios de pago
# ---------------------------------------------------------------------------
class MedioPagoListView(RequireClienteMixin, ListView):
    model = MedioPagoCliente
    template_name = "pagos/clientes_list.html"
    context_object_name = "medios"

    def get_queryset(self):  
        return (
            MedioPagoCliente.objects.select_related("tipo")
             .filter(cliente=self.cliente)  
            .order_by("-activo", "-predeterminado", "alias")
        )

class MedioPagoCreateView(RequireClienteMixin, CreateView):
    model = MedioPagoCliente
    form_class = MedioPagoClienteForm
    template_name = "pagos/clientes_form.html"
    success_url = reverse_lazy("pagos:clientes_list")

    def get_success_url(self):
        # Si hay un parámetro 'next' en la URL, redirigir a esa URL
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse("pagos:clientes_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        if self.request.method == "GET" and self.request.GET.get("tipo"):
            kwargs.setdefault("initial", {})["tipo"] = self.request.GET.get("tipo")
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.cliente = self.cliente
        obj.save()
        self.object = obj
        messages.success(self.request, "Medio de pago creado correctamente.")
        return redirect(self.get_success_url())

class MedioPagoUpdateView(RequireClienteMixin, UpdateView):
    model = MedioPagoCliente
    form_class = MedioPagoClienteForm
    template_name = "pagos/clientes_form.html"
    success_url = reverse_lazy("pagos:clientes_list")
    pk_url_kwarg = "id_medio"

    def get_queryset(self):
        return MedioPagoCliente.objects.filter(cliente=self.cliente) 

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse("pagos:clientes_list")

    def form_valid(self, form):
        self.object = form.save();
        messages.success(self.request, "Medio de pago actualizado correctamente.")
        return redirect(self.get_success_url())

class MedioPagoDeleteView(RequireClienteMixin, DeleteView):
    model = MedioPagoCliente
    template_name = "pagos/clientes_confirm_delete.html"
    success_url = reverse_lazy("pagos:clientes_list")
    pk_url_kwarg = "id_medio"

    def get_queryset(self):
        return MedioPagoCliente.objects.filter(cliente=self.cliente)

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return super().get_success_url()

class MedioPagoPredeterminarView(RequireClienteMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Bloqueamos filas del cliente para evitar carreras
                medio = (MedioPagoCliente.objects
                         .select_for_update()
                        .get(pk=kwargs.get("id_medio"), cliente=self.cliente, activo=True))

                # No permitir predeterminar si el tipo está inactivo
                if not medio.tipo.activo:
                    return HttpResponseForbidden("No permitido")

                # Si ya es predeterminado, nada que hacer (evita writes y errores)
                if medio.predeterminado:
                    return HttpResponseRedirect(reverse("pagos:clientes_list"))

                # Apagar cualquier otro predeterminado de este cliente
                (MedioPagoCliente.objects
                 .select_for_update()
                 .filter(cliente=self.cliente, predeterminado=True)
                 .exclude(pk=medio.pk)
                 .update(predeterminado=False, actualizado_en=now()))

                # Encender el elegido
                medio.predeterminado = True
                medio.actualizado_en = now()
                medio.save(update_fields=["predeterminado", "actualizado_en"])

        except MedioPagoCliente.DoesNotExist:
            return HttpResponseForbidden("No permitido")

        # Mejor redirigir para evitar reenvío del formulario y ver el cambio reflejado
        return HttpResponseRedirect(reverse("pagos:clientes_list"))

    def get(self, *args, **kwargs):
        return HttpResponseForbidden("Método no permitido")

class AjaxCreateMedioPagoView(RequireClienteMixin, View):
    """
    Vista AJAX para crear un nuevo MedioPagoCliente.
    Devuelve JSON con el nuevo medio si es exitoso, o el formulario con errores si falla.
    """
    def get(self, request, *args, **kwargs):
        cliente = self.cliente
        # Obtener el tipo de medio de pago si se pasa en la URL (para campos dinámicos)
        tipo_id = request.GET.get('tipo')
        initial_data = {}
        if tipo_id:
            initial_data['tipo'] = tipo_id
        
        form = MedioPagoClienteForm(initial=initial_data, user=request.user)
        form_html = render_to_string(
            "pagos/clientes_form_ajax.html",
            {'form': form, 'cliente': cliente},
            request=request
        )
        return JsonResponse({
            'success': True,
            'form_html': form_html,
        })

    def post(self, request, *args, **kwargs):
        cliente = self.cliente # Obtenido del RequireClienteMixin
        form = MedioPagoClienteForm(request.POST, user=request.user)

        if form.is_valid():
            medio_pago = form.save(commit=False)
            medio_pago.cliente = cliente
            medio_pago.save()

            # Preparar datos del nuevo medio para la respuesta JSON
            campos_data = []
            for campo in medio_pago.tipo.campos.filter(activo=True):
                campos_data.append({
                    'nombre_campo': campo.nombre_campo,
                    'valor': medio_pago.datos.get(campo.nombre_campo, ''),
                })

            return JsonResponse({
                'success': True,
                'id_medio': str(medio_pago.id_medio),
                'alias': medio_pago.alias,
                'tipo_nombre': medio_pago.tipo.nombre,
                'campos': campos_data,
                'message': "Medio de pago creado correctamente."
            })
        else:
            # Si el formulario no es válido, renderizarlo con errores y devolver el HTML
            form_html = render_to_string(
                "pagos/clientes_form_ajax.html",
                {'form': form, 'cliente': cliente},
                request=request
            )
            return JsonResponse({
                'success': False,
                'form_html': form_html,
                'message': "Por favor, corregí los errores en el formulario."
            })

class AjaxGetMedioPagoFormView(RequireClienteMixin, View):
    """
    Vista AJAX para obtener el HTML de un formulario de MedioPagoCliente (para edición/visualización).
    """
    def get(self, request, *args, **kwargs):
        cliente = self.cliente
        id_medio = kwargs.get('id_medio')
        
        try:
            medio_pago = MedioPagoCliente.objects.get(id_medio=id_medio, cliente=cliente)
            form = MedioPagoClienteForm(instance=medio_pago, user=request.user)
            
            form_html = render_to_string(
                "pagos/clientes_form_ajax.html",
                {'form': form, 'object': medio_pago, 'cliente': cliente}, # Pasar 'object' para que la plantilla sepa que es edición
                request=request
            )
            return JsonResponse({
                'success': True,
                'form_html': form_html,
            })
        except MedioPagoCliente.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': "Medio de pago no encontrado o no pertenece al cliente."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"Error al cargar el formulario: {str(e)}"
            }, status=500)
