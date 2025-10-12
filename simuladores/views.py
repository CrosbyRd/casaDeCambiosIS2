# simuladores/views.py
import json
import requests
from django.http import JsonResponse, Http404
from django.views import View
from django.urls import reverse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from .models import PedidoPagoSimulado
from transacciones.models import Transaccion

class IniciarPagoAPIView(View):
    """
    API View para iniciar un nuevo pedido de pago simulado.
    Imita el 'Paso 1' de una pasarela de pago.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"respuesta": False, "error": "Cuerpo de la petición inválido."}, status=400)

        # El 'id_pedido_comercio' de Pagopar es nuestro 'transaccion_id'
        transaccion_id = data.get('id_pedido_comercio')
        url_notificacion = data.get('url_confirmacion') # Mantenemos compatibilidad de nombres
        url_retorno = data.get('url_retorno')

        if not all([transaccion_id, url_notificacion, url_retorno]):
            return JsonResponse({"respuesta": False, "error": "Faltan datos requeridos (id_pedido_comercio, url_confirmacion, url_retorno)."}, status=400)

        try:
            # Verificamos que la transacción exista en nuestro sistema
            Transaccion.objects.get(id=transaccion_id)
        except Transaccion.DoesNotExist:
            return JsonResponse({"respuesta": False, "error": "Transacción no encontrada."}, status=404)

        # Creamos el pedido en nuestra pasarela simulada
        pedido, created = PedidoPagoSimulado.objects.update_or_create(
            transaccion_id=transaccion_id,
            defaults={
                'datos_pedido': data,
                'url_notificacion': url_notificacion,
                'url_retorno': url_retorno
            }
        )

        # Construimos la URL de redirección al checkout simulado
        url_redirect = request.build_absolute_uri(
            reverse('simuladores:pagina_pago', args=[pedido.hash])
        )
        
        # Respondemos de forma similar a Pagopar
        return JsonResponse({
            "respuesta": True,
            "resultado": [{"hash": pedido.hash, "url_redirect": url_redirect}]
        })

class PaginaPagoSimuladaView(TemplateView):
    """
    Muestra la página de checkout donde el usuario confirma el pago.
    """
    template_name = 'simuladores/pagina_pago.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_hash = self.kwargs['hash']
        
        try:
            pedido = PedidoPagoSimulado.objects.get(hash=pedido_hash)
            # Recuperamos la transacción original para mostrar sus datos
            context['transaccion'] = Transaccion.objects.get(id=pedido.transaccion_id)
            context['pedido_hash'] = pedido.hash
        except (PedidoPagoSimulado.DoesNotExist, Transaccion.DoesNotExist):
            raise Http404("Pedido de pago no encontrado")
            
        return context

class ConfirmarPagoSimuladoView(View):
    """
    Procesa la confirmación del pago y envía el webhook de notificación.
    """
    def post(self, request, *args, **kwargs):
        pedido_hash = self.kwargs['hash']
        
        try:
            pedido = PedidoPagoSimulado.objects.get(hash=pedido_hash)
            transaccion = Transaccion.objects.get(id=pedido.transaccion_id)
        except (PedidoPagoSimulado.DoesNotExist, Transaccion.DoesNotExist):
            return redirect('home') # O a una página de error

        # Actualizar estado de la transacción a "Pagada, Pendiente de Retiro"
        transaccion.estado = 'pendiente_retiro_tauser'
        transaccion.save()

        metodo_pago = request.POST.get('metodo_pago', 'desconocido')
        datos_adicionales = request.POST.get('datos_adicionales', '')

        # 1. Simular el Webhook de notificación (Paso 3 de Pagopar)
        try:
            requests.post(
                pedido.url_notificacion, 
                json={
                    "respuesta": True,
                    "resultado": [{
                        "pagado": True,
                        "hash_pedido": str(pedido.hash),
                        "numero_pedido": str(transaccion.id), # Asegurarse que sea string
                        "monto": f"{transaccion.monto_origen:.2f}",
                        "metodo_pago_simulado": metodo_pago,
                        "datos_adicionales_simulados": datos_adicionales,
                        # ... otros campos para imitar la respuesta
                    }]
                },
                timeout=5
            )
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar el webhook de notificación: {e}")

        # 2. Limpiar el pedido simulado
        pedido.delete()
        
        # 3. Redirigir al usuario a la página de retorno (Paso 4 de Pagopar)
        return redirect(pedido.url_retorno)
