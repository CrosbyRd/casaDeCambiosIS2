# simuladores/views.py
import json
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import PagoSimulado
from notificaciones.models import Notificacion
from transacciones.models import Transaccion


# simuladores/views.py

class PaginaPagoSimuladaView(TemplateView):
    template_name = 'simuladores/pagina_pago.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pago_id = self.kwargs['transaccion_id']
        pago = get_object_or_404(PagoSimulado, id=pago_id, estado='PENDIENTE')
        context['pago'] = pago

        transaccion = get_object_or_404(Transaccion, id=pago.referencia_comercio)
        context['transaccion'] = transaccion

        # 🔔 Solo notificaciones relevantes para esta transacción
        notificaciones = []
        if self.request.user.is_authenticated:
            ahora = timezone.now()
            if transaccion.estado in [
                'pendiente_pago_cliente',
                'pendiente_retiro_tauser',
                'pendiente_deposito_tauser',
            ]:
                # Solo notificaciones creadas después de la transacción
                notificaciones = (
                    Notificacion.objects.filter(
                        destinatario=self.request.user,
                        leida=False,
                        fecha_creacion__gte=transaccion.fecha_creacion,
                        mensaje__icontains="ha cambiado"
                    )
                    .order_by('-fecha_creacion')[:1]  # solo la más reciente
                )
        context['notificaciones'] = notificaciones
        return context




class ConfirmarPagoSimuladoView(View):
    """
    Procesa la confirmación del usuario, envía el webhook y redirige.
    """

    def post(self, request, *args, **kwargs):
        pago_id = self.kwargs['transaccion_id']
        pago = get_object_or_404(PagoSimulado, id=pago_id, estado='PENDIENTE')

        accion = request.POST.get("accion")

        if accion == "pagar":
            estado_final = "EXITOSO"
        elif accion == "cancelar":
            estado_final = "RECHAZADO"
        else:
            return HttpResponseBadRequest("Acción no válida.")

        # Enviar Webhook a través del orquestador de pagos
        from pagos.services import handle_payment_webhook
        webhook_payload = {
            'transaccion_id_pasarela': str(pago.id),
            'referencia_comercio': str(pago.referencia_comercio),
            'estado': estado_final,
            'monto': str(pago.monto)
        }

        handle_payment_webhook(webhook_payload)

        # Actualizar estado del pago simulado y redirigir
        pago.estado = 'PROCESADO'
        pago.save()

        return redirect(pago.url_retorno)
