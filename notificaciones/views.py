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
def marcar_notificaciones_leidas(request):
    """
    Marca todas las notificaciones no leídas del usuario autenticado como leídas.
    Devuelve un JSON indicando éxito.
    """
    Notificacion.objects.filter(destinatario=request.user, leida=False).update(leida=True)
    return JsonResponse({"ok": True})
# notificaciones/views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from notificaciones.models import Notificacion

@login_required
def marcar_leidas(request):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        Notificacion.objects.filter(destinatario=request.user, leida=False, tipo='tasa').update(leida=True, fecha_lectura=timezone.now())
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notificacion

@login_required

def ver_nuevas(request):
    """
    Devuelve la última notificación de tipo 'tasa' no leída para el usuario.
    Una vez que se devuelve, la marca como leída para no volver a mostrarla.
    """
    # Buscamos la notificación más reciente de tipo 'tasa' que no haya sido leída.
    noti = Notificacion.objects.filter(
        destinatario=request.user, 
        leida=False, 
        tipo='tasa'
    ).order_by('-fecha_creacion').first()
    
    if noti:
        # ¡Paso clave! La marcamos como leída para que no vuelva a aparecer.
        noti.leida = True
        noti.save(update_fields=['leida'])
        
        # Devolvemos el mensaje para que el frontend lo muestre.
        return JsonResponse({"mensaje": noti.mensaje, "id": noti.id})
    
    # No hay notificaciones nuevas
    return JsonResponse({})