from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .utils import get_cliente_activo

class RequireClienteMixin(LoginRequiredMixin):
    cliente: object = None  # se setea en dispatch

    def dispatch(self, request, *args, **kwargs):
        self.cliente = get_cliente_activo(request)
        if not self.cliente:
            messages.info(request, "Seleccioná con qué cliente querés operar.")
            # podés pasar next= para volver luego
            return redirect("usuarios:seleccionar_cliente")
        return super().dispatch(request, *args, **kwargs)
