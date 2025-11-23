"""
Vistas de la aplicación **medios_acreditacion**.

.. module:: medios_acreditacion.views
   :synopsis: Gestión de tipos de medios de acreditación y medios asociados a clientes.

Este módulo implementa las vistas basadas en clases para administrar
los **tipos de medios de acreditación** (sección administrativa) y los
**medios de acreditación de clientes** (sección cliente).
Incluye control de permisos, manejo de formsets y operaciones CRUD
con notificaciones al usuario.
"""
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.forms import inlineformset_factory
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from usuarios.mixins import RequireClienteMixin
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views import View
from django.shortcuts import get_object_or_404


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



# ===== Mixin de acceso solo admin de esta sección =====
class AccessMediosAcreditacionMixin:
    """
        Mixin de control de acceso para la sección administrativa de medios de acreditación.

        Requiere que el usuario esté autenticado y posea el permiso
        ``medios_acreditacion.access_medios_acreditacion``.

        **Atributos**
        -------------
        required_permission : str
            El permiso necesario para permitir el acceso.

        **Métodos**
        -----------
        dispatch(request, *args, **kwargs) -> HttpResponse or HttpResponseRedirect
            Verifica que el usuario esté autenticado (por medio de @login_required)
            y posea el permiso `required_permission`. Si no lo tiene, redirige a la vista "home".
            En caso contrario, delega al método dispatch de la clase base.
    """
    required_permission = "medios_acreditacion.access_medios_acreditacion"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm(self.required_permission):
            # mismo comportamiento que tus otras apps: fuera -> home
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

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
"""
    Formset inline para administrar instancias de :class:`CampoMedioAcreditacion`
    relacionadas con un :class:`TipoMedioAcreditacion`.

    Se utiliza en las vistas de creación y edición de tipos de medio.

    **Opciones principales**
    ------------------------
    - ``extra = 0``: no genera filas vacías automáticamente.
    - ``can_delete = True``: permite marcar instancias para borrado.
"""
class TipoMedioListView(AccessMediosAcreditacionMixin, ListView):
    """
        Vista para listar los tipos de medios de acreditación (administración).

        Requiere permiso administrativo (hereda AccessMediosAcreditacionMixin).

        **Atributos**
        -------------
        model : Modelo
            Modelo asociado: :class:`TipoMedioAcreditacion`.
        template_name : str
            Ruta del template: "medios_acreditacion/tipos_list.html".
        context_object_name : str
            Nombre del objeto en el contexto de plantilla: "tipos".
    """
    model = TipoMedioAcreditacion
    template_name = "medios_acreditacion/tipos_list.html"
    context_object_name = "tipos"


class TipoMedioCreateView(AccessMediosAcreditacionMixin, CreateView):
    """
        Vista para crear un nuevo tipo de medio de acreditación, junto con sus campos asociados.

        Se apoya en un formset inline (CampoFormSet) para definir múltiples campos en el mismo formulario.

        **Atributos**
        -------------
        model : Modelo
            Modelo asociado: :class:`TipoMedioAcreditacion`.
        form_class : Formulario
            Formulario principal: :class:`TipoMedioForm`.
        template_name : str
            Template: "medios_acreditacion/tipos_form.html".
        success_url : str
            URL a la que redirigir tras exitoso guardado: reverse_lazy("medios_acreditacion:tipos_list").

        **Métodos**
        -----------
        get_context_data(**kwargs) -> dict
            Agrega el formset al contexto y una clave "accion" con valor "crear".

        form_valid(form) -> HttpResponseRedirect or HttpResponse
            - Guarda el objeto padre (tipo de medio).
            - Reconstruye el formset con esa instancia.
            - Valida el formset.
            - Si hay errores: muestra mensajes de error y re-renderiza con el formset con errores.
            - Si es válido: guarda los objetos, marca `activo = True`, borra los eliminados, muestra mensaje éxito,
            y redirige a `success_url`.
    """
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

    
    

class TipoMedioUpdateView(AccessMediosAcreditacionMixin, UpdateView):
    """
        Vista para editar un tipo de medio de acreditación existente, junto con sus campos asociados.

        Mantiene los campos existentes, permite borrado lógico y reactivación.

        **Atributos**
        -------------
        model : Modelo
            :class:`TipoMedioAcreditacion`
        form_class : Formulario
            :class:`TipoMedioForm`
        template_name : str
            Template: "medios_acreditacion/tipos_form.html"
        success_url : str
            URL de redirección tras éxito.

        **Métodos**
        -----------
        get_context_data(**kwargs) -> dict
            Crea el formset ya sea con datos POST o con la instancia existente para edición,
            agrega clave "accion" = "editar".

        form_valid(form) -> HttpResponseRedirect or HttpResponse
            - Valida el formset; si hay errores, construye mensajes con el índice de fila.
            - Guarda primero el tipo de medio.
            - Obtiene instancias del formset (commit=False) y las guarda, asignando tipo_medio.
            - Marca los objetos “eliminados” como `activo = False` en vez de borrarlos.
            - Reactiva las instancias que estaban inactivas y no fueron marcadas como DELETE.
            - Muestra mensaje éxito y redirige.
    """


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


class TipoMedioDeleteView(AccessMediosAcreditacionMixin, DeleteView):
    """
    Vista para eliminar un tipo de medio de acreditación.

    Presenta una confirmación y luego ejecuta el borrado.

    **Atributos**
    -------------
    model : Modelo
        :class:`TipoMedioAcreditacion`
    template_name : str
        Template de confirmación: "medios_acreditacion/tipos_confirm_delete.html"
    success_url : str
        URL de redirección tras la eliminación: lista de tipos.

    **Métodos**
    -----------
    delete(request, *args, **kwargs) -> HttpResponseRedirect
        Al borrar, muestra mensaje de éxito, luego delega al método `delete`
        de la clase base.
    """
    model = TipoMedioAcreditacion
    template_name = "medios_acreditacion/tipos_confirm_delete.html"
    success_url = reverse_lazy("medios_acreditacion:tipos_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tipo de medio eliminado correctamente ❌")
        return super().delete(request, *args, **kwargs)

# =====================================================
# VISTAS PARA MEDIOS DE CLIENTES (lado cliente)
# =====================================================
class MedioClienteListView(RequireClienteMixin, ListView):
    """
    Vista para listar los medios de acreditación asociados a un cliente logueado.

    Requiere que el usuario corresponda a un cliente (RequireClienteMixin).

    **Atributos**
    -------------
    model : Modelo
        :class:`MedioAcreditacionCliente`
    template_name : str
        Template: "medios_acreditacion/clientes_list.html"
    context_object_name : str
        Nombre del objeto en contexto: "medios"

    **Métodos**
    -----------
    get_queryset() -> QuerySet
        Retorna solo los medios del cliente actual, usando `select_related("tipo")`.
    """
    model = MedioAcreditacionCliente
    template_name = "medios_acreditacion/clientes_list.html"
    context_object_name = "medios"

    def get_queryset(self):
        return (super().get_queryset()
                .filter(cliente=self.cliente)
                .select_related("tipo"))

class MedioClienteCreateView(RequireClienteMixin, CreateView):
    """
    Vista para que un cliente cree un nuevo medio de acreditación.

    **Atributos**
    -------------
    model : Modelo
        :class:`MedioAcreditacionCliente`
    form_class : Formulario
        :class:`MedioAcreditacionClienteForm`
    template_name : str
        Template: "medios_acreditacion/clientes_form.html"
    success_url : str
        URL de redirección tras guardado exitoso.

    **Métodos**
    -----------
    get_initial() -> dict
        Si se pasa un parámetro GET `tipo`, lo preasigna en los valores iniciales del formulario.

    form_valid(form) -> HttpResponseRedirect
        Asigna `cliente` al formulario antes de guardar.

    get_form_kwargs() -> dict
        Agrega `user` al contexto del formulario para validaciones internas.
        Si hay parámetro GET `tipo`, preasigna ese tipo si existe.

    get_context_data(**kwargs) -> dict
        Agrega `"accion": "crear"` al contexto.
    """

    model = MedioAcreditacionCliente
    form_class = MedioAcreditacionClienteForm
    template_name = "medios_acreditacion/clientes_form.html"
    success_url = reverse_lazy("medios_acreditacion:clientes_list")



    def get_initial(self):
        initial = super().get_initial()
        tipo = self.request.GET.get("tipo")
        if tipo:
            initial["tipo"] = tipo
        return initial

    def form_valid(self, form):
        form.instance.cliente = self.cliente
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user   # ahora el form lo acepta
        # Para que al cambiar el select muestre campos dinámicos
        tipo_id = self.request.GET.get("tipo")
        if tipo_id:
            try:
                kwargs.setdefault("initial", {})
                kwargs["initial"]["tipo"] = TipoMedioAcreditacion.objects.get(pk=tipo_id)
            except TipoMedioAcreditacion.DoesNotExist:
                pass
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["accion"] = "crear"
        return ctx


class MedioClienteUpdateView(RequireClienteMixin, UpdateView):
    """
    Vista para que un cliente edite un medio de acreditación suyo.

    **Atributos**
    -------------
    model : Modelo
        :class:`MedioAcreditacionCliente`
    form_class : Formulario
        :class:`MedioAcreditacionClienteForm`
    template_name : str
        Template: "medios_acreditacion/clientes_form.html"
    success_url : str
        URL de redirección tras edición.

    **Métodos**
    -----------
    get_queryset() -> QuerySet
        Restringe para que el cliente solo pueda editar sus propios medios.

    get_form_kwargs() -> dict
        Agrega `user` al contexto del formulario.

    get_context_data(**kwargs) -> dict
        Agrega `"accion": "editar"` al contexto.

    form_valid(form) -> HttpResponseRedirect
        Asegura que `cliente` esté asignado antes de guardar, y añade mensaje de éxito.
    """
    model = MedioAcreditacionCliente
    form_class = MedioAcreditacionClienteForm
    template_name = "medios_acreditacion/clientes_form.html"
    success_url = reverse_lazy("medios_acreditacion:clientes_list")

    def get_queryset(self):
        return super().get_queryset().filter(cliente=self.cliente)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["accion"] = "editar"
        return ctx

    def form_valid(self, form):
        form.instance.cliente = self.cliente
        messages.success(self.request, "Medio de acreditación actualizado correctamente ✏️")
        return super().form_valid(form)

class MedioClienteDeleteView(RequireClienteMixin, DeleteView):
    """
    Vista para que un cliente elimine uno de sus medios de acreditación.

    **Atributos**
    -------------
    model : Modelo
        :class:`MedioAcreditacionCliente`
    template_name : str
        Template: "medios_acreditacion/clientes_confirm_delete.html"
    success_url : str
        URL de redirección tras eliminar.

    **Métodos**
    -----------
    get_queryset() -> QuerySet
        Restringe el queryset al cliente logueado.

    delete(request, *args, **kwargs) -> HttpResponseRedirect
        Muestra mensaje de éxito y delega al método base.
    """
    model = MedioAcreditacionCliente
    template_name = "medios_acreditacion/clientes_confirm_delete.html"
    success_url = reverse_lazy("medios_acreditacion:clientes_list")

    def get_queryset(self):
        return super().get_queryset().filter(cliente=self.cliente)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Medio de acreditación eliminado correctamente ❌")
        return super().delete(request, *args, **kwargs)
    


class MedioClientePredeterminarView(RequireClienteMixin, View):
    """
    Vista para que un cliente marque como predeterminado uno de sus medios de acreditación.

    Esta vista responde solo a solicitudes POST; no permite GET.

    **Métodos**
    -----------
    post(request, pk) -> HttpResponse or HttpResponseBadRequest
        - Busca el medio con pk y cliente correspondiente.
        - Verifica que esté activo; si no, retorna Bad Request (400).
        - Marca `predeterminado = True` en el objeto (el modelo debería encargarse
          de desmarcar otros si es necesario) y lo guarda.
        - Responde con estado 204 (sin contenido) dado que usualmente se usa vía JS/AJAX.

    get(request, pk) -> HttpResponseForbidden
        No está permitido acceder por GET: devuelve 403.
    """
    def post(self, request, pk):
        # obtener el medio del cliente logueado
        medio = get_object_or_404(
            MedioAcreditacionCliente.objects.filter(cliente=self.cliente), pk=pk
        )
        if not medio.activo:
            return HttpResponseBadRequest("Medio inactivo.")
        # marcar y desmarcar otros (lo hace su save())
        medio.predeterminado = True
        medio.save()
        # status 204: sin contenido; tu JS hace reload de la página
        return HttpResponse(status=204)

    def get(self, request, pk):
        # no permitimos GET para esta acción
        return HttpResponseForbidden()