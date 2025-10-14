# transacciones/views.py
import json
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from .models import Transaccion

@method_decorator(csrf_exempt, name='dispatch')
class WebhookConfirmacionPagoView(View):
    """
    Endpoint que recibe la notificación (webhook) desde la pasarela de pagos.
    Actualiza el estado de la transacción según el resultado del pago.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            print(f"INFO: [WEBHOOK] Webhook recibido: {data}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Cuerpo de la petición inválido."}, status=400)

        # Extraer datos del webhook
        transaccion_id = data.get('referencia_comercio')
        estado_pago = data.get('estado')

        if not transaccion_id or not estado_pago:
            return JsonResponse({"error": "Faltan 'referencia_comercio' o 'estado' en el webhook."}, status=400)

        # Buscar la transacción en la base de datos
        transaccion = get_object_or_404(Transaccion, id=transaccion_id)

        # Actualizar el estado de la transacción
        if transaccion.estado == 'pendiente_pago_cliente':
            if estado_pago == 'EXITOSO':
                transaccion.estado = 'pendiente_retiro_tauser'
                print(f"INFO: [WEBHOOK] Transacción {transaccion.id} actualizada a 'pendiente_retiro_tauser'.")
            elif estado_pago == 'RECHAZADO':
                transaccion.estado = 'cancelada'
                print(f"INFO: [WEBHOOK] Transacción {transaccion.id} actualizada a 'cancelada'.")
            
            transaccion.save()
        else:
            # Evita procesar el webhook dos veces si ya se actualizó el estado
            print(f"WARN: [WEBHOOK] La transacción {transaccion.id} ya no estaba pendiente de pago. Estado actual: {transaccion.estado}")

        return JsonResponse({"status": "ok"})

class ResultadoPagoView(TemplateView):
    """
    Muestra al cliente el resultado de su operación de pago después de ser
    redirigido desde la pasarela.
    """
    template_name = 'transacciones/resultado_pago.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transaccion_id = self.kwargs['transaccion_id']
        transaccion = get_object_or_404(Transaccion, id=transaccion_id)
        context['transaccion'] = transaccion
        return context
