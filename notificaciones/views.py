# notificaciones/views.py (NUEVO ARCHIVO)
"""
Módulo de vistas para la aplicación de notificaciones.

Contiene las vistas basadas en clases que permiten:
- Mostrar las notificaciones de un usuario autenticado.
- Editar sus preferencias de notificación.
- Gestionar acciones de interacción como marcar notificaciones como leídas o silenciarlas mediante peticiones AJAX (JSON).


"""

from pyexpat.errors import messages
from django.views.generic import ListView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

from .models import Notificacion, PreferenciasNotificacion
from .forms import PreferenciasNotificacionForm

class NotificacionListView(LoginRequiredMixin, ListView):
    """
    Vista que lista las **notificaciones activas** (no silenciadas) del usuario autenticado.

    :cvar model: Modelo asociado a la vista.
    :type model: notificaciones.models.Notificacion
    :cvar template_name: Ruta del template HTML utilizado.
    :type template_name: str
    :cvar context_object_name: Nombre del contexto que contendrá la lista de notificaciones.
    :type context_object_name: str
    :cvar paginate_by: Cantidad de notificaciones mostradas por página.
    :type paginate_by: int
    """

    model = Notificacion
    template_name = 'notificaciones/notificacion_list.html'
    context_object_name = 'notificaciones'
    paginate_by = 15

    def get_queryset(self):
        # Mostrar solo las no silenciadas del usuario logueado
        return super().get_queryset().filter(
            destinatario=self.request.user,
            silenciada=False
        )

class PreferenciasNotificacionUpdateView(LoginRequiredMixin, UpdateView):
    """
    Vista para **editar las preferencias de notificación** del usuario actual.

    Utiliza un formulario basado en :class:`PreferenciasNotificacionForm` y actualiza
    el objeto :class:`PreferenciasNotificacion` vinculado al usuario autenticado.

    :cvar model: Modelo de preferencias de notificación.
    :type model: notificaciones.models.PreferenciasNotificacion
    :cvar form_class: Clase de formulario asociada.
    :type form_class: notificaciones.forms.PreferenciasNotificacionForm
    :cvar template_name: Plantilla HTML utilizada.
    :type template_name: str
    :cvar success_url: URL a la cual se redirige tras la actualización exitosa.
    :type success_url: str
    """
    model = PreferenciasNotificacion
    form_class = PreferenciasNotificacionForm
    template_name = 'notificaciones/preferencias_form.html'
    success_url = reverse_lazy('notificaciones:preferencias') # Redirigir a la misma página

    def get_object(self, queryset=None):
        # Obtener o crear el objeto de preferencias para el usuario actual
        obj, created = PreferenciasNotificacion.objects.get_or_create(usuario=self.request.user)
        return obj

    def form_valid(self, form):
        # Aquí puedes añadir un mensaje de éxito
        messages.success(self.request, "Tus preferencias de notificación han sido actualizadas.")
        return super().form_valid(form)

# --- Vistas para API (interacción con Javascript) ---

class SilenciarNotificacionView(LoginRequiredMixin, View):
    """
    Vista que permite **silenciar una notificación** mediante una solicitud AJAX (POST).

    Cambia el estado de `silenciada` a ``True`` para ocultarla del tablón principal.

    :param request: Objeto HttpRequest recibido.
    :type request: django.http.HttpRequest
    :param pk: Clave primaria de la notificación a silenciar.
    :type pk: uuid.UUID
    :returns: Respuesta JSON con el resultado de la operación.
    :rtype: django.http.JsonResponse
    """
    def post(self, request, pk):
        notificacion = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
        notificacion.silenciada = True
        notificacion.save()
        return JsonResponse({'status': 'ok', 'message': 'Notificación silenciada.'})

class MarcarLeidaNotificacionView(LoginRequiredMixin, View):
    """
    Vista que permite **marcar una notificación como leída** mediante una solicitud AJAX (POST).

    Si la notificación aún no fue leída, se actualiza el campo `leida` a ``True``.

    :param request: Objeto HttpRequest recibido.
    :type request: django.http.HttpRequest
    :param pk: Clave primaria de la notificación a marcar como leída.
    :type pk: uuid.UUID
    :returns: Respuesta JSON con el resultado de la operación.
    :rtype: django.http.JsonResponse
    """
    def post(self, request, pk):
        notificacion = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save()
        return JsonResponse({'status': 'ok', 'message': 'Notificación marcada como leída.'})
