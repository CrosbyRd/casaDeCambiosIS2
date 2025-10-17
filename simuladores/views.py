# simuladores/views.py
import json
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from .models import PagoSimulado
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class PaginaPagoSimuladaView(TemplateView):
    """
    Renderiza la pรกgina HTML donde el usuario "paga" (confirma o cancela).
    """
    template_name = 'simuladores/pagina_pago.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pago_id = self.kwargs['transaccion_id']
        pago = get_object_or_404(PagoSimulado, id=pago_id, estado='PENDIENTE')
        
        context['pago'] = pago
        
        # Obtener la transacciรณn real asociada al pago simulado
        from transacciones.models import Transaccion
        try:
            transaccion = get_object_or_404(Transaccion, id=pago.referencia_comercio)
            context['transaccion'] = transaccion
        except Transaccion.DoesNotExist:
            context['error'] = "No se encontrรณ la transacciรณn asociada a este pago."

        return context

class ConfirmarPagoSimuladoView(View):
    """
    Procesa la confirmaciรณn del usuario, envรญa el webhook y redirige.
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
        
        # Llamar al orquestador para manejar el webhook
        handle_payment_webhook(webhook_payload)

        # Actualizar estado del pago simulado y redirigir
        pago.estado = 'PROCESADO'
        pago.save()
        
        return redirect(pago.url_retorno)
