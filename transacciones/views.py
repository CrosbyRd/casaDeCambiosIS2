# transacciones/views.py
import json
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages

from .models import Transaccion
from pagos.services import iniciar_cobro_a_cliente
from usuarios.utils import get_cliente_activo
from pagos.models import TipoMedioPago


class IniciarCompraDivisaView(LoginRequiredMixin, TemplateView):
    """
    Vista para que el cliente inicie una transacción de compra de divisas.
    """
    template_name = 'transacciones/iniciar_compra_divisa.html' # Crear esta plantilla
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aquí se podría añadir lógica para formularios, datos iniciales, etc.
        return context

class IniciarPagoTransaccionView(LoginRequiredMixin, View):
    """
    Vista para que el cliente inicie el proceso de pago para una transacción
    de venta de divisa (compra de la casa de cambio) que está pendiente de pago.
    """
    def post(self, request, transaccion_id, *args, **kwargs):
        cliente_activo = get_cliente_activo(request)
        transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=cliente_activo)

        if transaccion.tipo_operacion == 'venta' and transaccion.estado == 'pendiente_pago_cliente':
            # Obtener el medio de pago utilizado en la transacción
            medio_pago_id = transaccion.medio_pago_utilizado.id_tipo if transaccion.medio_pago_utilizado else None
            
            if not medio_pago_id:
                messages.error(request, "No se especificó un medio de pago para esta transacción.")
                return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

            url_pago = iniciar_cobro_a_cliente(transaccion, request, medio_pago_id=medio_pago_id)
            if url_pago:
                return redirect(url_pago)
            else:
                transaccion.estado = 'error'
                transaccion.save()
                messages.error(request, "No se pudo iniciar el proceso de pago. Por favor, intente nuevamente más tarde.")
                return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
        else:
            messages.warning(request, "Esta transacción no está en un estado válido para iniciar el pago.")
            return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

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

        # Si la transacción está pendiente de pago, intentar obtener la URL de la pasarela
        if transaccion.estado == 'pendiente_pago_cliente' and transaccion.medio_pago_utilizado:
            # Llamar al orquestador para obtener la URL de pago
            # No se crea una nueva transacción, solo se obtiene la URL para la existente
            url_continuar_pago = iniciar_cobro_a_cliente(transaccion, self.request, medio_pago_id=str(transaccion.medio_pago_utilizado.id_tipo))
            context['url_continuar_pago'] = url_continuar_pago
        
        return context
