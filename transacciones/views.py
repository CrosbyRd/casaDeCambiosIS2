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
from decimal import Decimal # Necesario para manejar Decimal

from .models import Transaccion
from pagos.services import iniciar_cobro_a_cliente
from usuarios.utils import get_cliente_activo, send_otp_email, validate_otp_code # Importar funciones OTP
from usuarios.forms import VerificacionForm # Importar formulario de verificación
from pagos.models import TipoMedioPago
from cotizaciones.models import Cotizacion # Para obtener la tasa en tiempo real


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
    Vista para que el cliente inicie el proceso de pago para una transacción.
    Incluye la verificación MFA para el Flujo B (Tasa Flotante).
    """
    template_name = 'transacciones/verificar_otp_pago.html' # Nueva plantilla para OTP

    def get(self, request, transaccion_id, *args, **kwargs):
        cliente_activo = get_cliente_activo(request)
        transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=cliente_activo)

        # Solo si es tasa flotante y pendiente de confirmación, se pide OTP
        if transaccion.modalidad_tasa == 'flotante' and transaccion.estado == 'pendiente_confirmacion_pago':
            send_otp_email(
                request.user,
                "Confirmación de Pago Final",
                "Tu código de verificación para confirmar el pago es: {code}. Válido por {minutes} minutos."
            )
            messages.info(request, f"Hemos enviado un código de verificación a tu email ({request.user.email}).")
            form = VerificacionForm()
            return render(request, self.template_name, {'form': form, 'email': request.user.email, 'transaccion': transaccion})
        
        # Si no requiere OTP o ya está en estado de pago, redirigir directamente a iniciar el cobro
        # Esto cubre el Flujo A (tasa bloqueada) y reintentos de pago
        return self._iniciar_cobro(request, transaccion)

    def post(self, request, transaccion_id, *args, **kwargs):
        cliente_activo = get_cliente_activo(request)
        transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=cliente_activo)

        # Lógica de verificación OTP para Flujo B
        if transaccion.modalidad_tasa == 'flotante' and transaccion.estado == 'pendiente_confirmacion_pago':
            form = VerificacionForm(request.POST)
            if form.is_valid():
                codigo = form.cleaned_data['codigo']
                if validate_otp_code(request.user, codigo):
                    # OTP válido, proceder con la actualización de tasa y el cobro
                    request.user.verification_code = None # Limpiar código OTP del usuario
                    request.user.code_created_at = None
                    request.user.save(update_fields=['verification_code', 'code_created_at']) # Guardar cambios en el usuario
                    
                    transaccion.estado = 'pendiente_pago_cliente' # Cambiar estado de la transacción a pendiente de pago
                    transaccion.save(update_fields=['estado']) # Guardar solo el estado en la transacción
                    messages.success(request, "Código OTP verificado. Procediendo con el pago.")
                    return self._iniciar_cobro(request, transaccion)
                else:
                    messages.error(request, "Código OTP incorrecto o expirado.")
            else:
                messages.error(request, "Por favor, ingresa un código válido.")
            return render(request, self.template_name, {'form': form, 'email': request.user.email, 'transaccion': transaccion})
        
        # Si no es tasa flotante o ya pasó la verificación OTP, proceder directamente
        return self._iniciar_cobro(request, transaccion)

    def _iniciar_cobro(self, request, transaccion):
        """
        Lógica para actualizar la tasa (si es flotante) e iniciar el cobro.
        """
        if transaccion.tipo_operacion == 'venta' and transaccion.estado == 'pendiente_pago_cliente':
            # Si la modalidad de tasa es flotante, actualizar la tasa de cambio aplicada con la tasa final
            if transaccion.modalidad_tasa == 'flotante':
                try:
                    cotizacion = Cotizacion.objects.get(
                        moneda_base=transaccion.moneda_origen,
                        moneda_destino=transaccion.moneda_destino
                    )
                    transaccion.tasa_cambio_aplicada = cotizacion.total_venta
                    transaccion.monto_destino = transaccion.monto_origen / cotizacion.total_venta
                    transaccion.save(update_fields=['tasa_cambio_aplicada', 'monto_destino'])
                    messages.info(request, f"Tasa de cambio actualizada a {cotizacion.total_venta} (final con comisiones) para la operación flotante.")
                except Cotizacion.DoesNotExist:
                    messages.error(request, "No se encontró una cotización válida para actualizar la tasa.")
                    return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
                except Exception as e:
                    messages.error(request, f"Error al actualizar la tasa de cambio: {e}")
                    return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

            medio_pago_id = transaccion.medio_pago_utilizado.id_tipo if transaccion.medio_pago_utilizado else None
            
            if not medio_pago_id:
                messages.error(request, "No se especificó un medio de pago para esta transacción.")
                return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

            url_pago = iniciar_cobro_a_cliente(transaccion, request, medio_pago_id=medio_pago_id)
            if url_pago:
                return redirect(url_pago)
            else:
                transaccion.estado = 'error'
                transaccion.save(update_fields=['estado'])
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
