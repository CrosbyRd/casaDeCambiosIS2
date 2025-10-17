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
            # Si la modalidad de tasa es flotante, actualizar la tasa de cambio aplicada
            if transaccion.modalidad_tasa == 'flotante':
                from cotizaciones.models import Cotizacion
                try:
                    # Obtener la cotización actual para la moneda de origen (PYG) y destino (USD)
                    # Asumimos que la moneda de origen es PYG y la de destino es la divisa extranjera
                    cotizacion = Cotizacion.objects.get(
                        moneda_base=transaccion.moneda_origen,
                        moneda_destino=transaccion.moneda_destino
                    )
                    # Actualizar la tasa de cambio aplicada con el valor de venta total (incluyendo comisiones)
                    transaccion.tasa_cambio_aplicada = cotizacion.total_venta
                    # Recalcular el monto destino con la nueva tasa final
                    transaccion.monto_destino = transaccion.monto_origen / cotizacion.total_venta
                    transaccion.save()
                    messages.info(request, f"Tasa de cambio actualizada a {cotizacion.total_venta} (final con comisiones) para la operación flotante.")
                except Cotizacion.DoesNotExist:
                    messages.error(request, "No se encontró una cotización válida para actualizar la tasa.")
                    return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
                except Exception as e:
                    messages.error(request, f"Error al actualizar la tasa de cambio: {e}")
                    return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

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

        # Delegar el procesamiento del webhook al orquestador de pagos
        from pagos.services import handle_payment_webhook
        result = handle_payment_webhook(data) # Pasar el payload completo al orquestador

        # El orquestador ya actualizó el estado de la transacción.
        # Aquí solo devolvemos la respuesta adecuada al emisor del webhook.
        if result.get('status') == 'ERROR':
            print(f"ERROR: [WEBHOOK] Error al procesar webhook: {result.get('message', 'Error desconocido')}")
            return JsonResponse({"error": result.get('message', 'Error al procesar webhook.')}, status=500)
        
        return JsonResponse({"status": "ok", "message": result.get('message', 'Webhook procesado.')})

class ResultadoPagoView(TemplateView):
    """
    Muestra al cliente el resultado de su operación de pago después de ser
    redirigido desde la pasarela.
    """
    template_name = 'transacciones/resultado_pago.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transaccion_id = self.kwargs['transaccion_id']
        # Recargar la transacción para asegurar que tenemos el estado más reciente
        transaccion = get_object_or_404(Transaccion, id=transaccion_id)
        transaccion.refresh_from_db() # Recargar la instancia desde la base de datos
        
        context['transaccion'] = transaccion
        context['url_continuar_pago'] = None # Inicializar a None

        # Solo ofrecer continuar pago si la transacción está *realmente* pendiente de pago
        # y tiene un medio de pago asociado.
        if transaccion.estado == 'pendiente_pago_cliente' and transaccion.medio_pago_utilizado:
            # Llamar al orquestador para obtener la URL de pago
            # No se crea una nueva transacción, solo se obtiene la URL para la existente
            url_continuar_pago = iniciar_cobro_a_cliente(transaccion, self.request, medio_pago_id=str(transaccion.medio_pago_utilizado.id_tipo))
            context['url_continuar_pago'] = url_continuar_pago
        
        return context
