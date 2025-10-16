# notificaciones/views.py (NUEVO ARCHIVO)
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
    def post(self, request, pk):
        notificacion = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
        notificacion.silenciada = True
        notificacion.save()
        return JsonResponse({'status': 'ok', 'message': 'Notificación silenciada.'})

class MarcarLeidaNotificacionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notificacion = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
        if not notificacion.leida:
            notificacion.leida = True
            notificacion.save()
        return JsonResponse({'status': 'ok', 'message': 'Notificación marcada como leída.'})
