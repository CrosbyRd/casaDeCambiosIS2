# simuladores/views.py
import json
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views import View
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from .models import PagoSimulado

class IniciarPagoAPIView(View):
    """
    Endpoint API que recibe la solicitud de inicio de pago y crea un registro
    en la base de datos para persistir la sesión de pago.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Cuerpo de la petición inválido."}, status=400)

        required_keys = ["monto", "moneda", "descripcion", "referencia_comercio", "url_confirmacion", "url_retorno"]
        if not all(key in data for key in required_keys):
            return JsonResponse({"error": "Faltan datos requeridos."}, status=400)

        # Crear el objeto de pago en la base de datos
        pago = PagoSimulado.objects.create(
            referencia_comercio=data['referencia_comercio'],
            monto=data['monto'],
            moneda=data['moneda'],
            descripcion=data['descripcion'],
            url_confirmacion=data['url_confirmacion'],
            url_retorno=data['url_retorno']
        )
        
        print(f"INFO: [SIMULADOR] PagoSimulado creado: {pago.id}")

        # Construir la URL de redirección a la página de pago
        url_redirect = request.build_absolute_uri(
            reverse('simuladores:pagina_pago', args=[pago.id])
        )
        
        return JsonResponse({
            "status": "ok",
            "transaccion_id": pago.id,
            "url_redirect": url_redirect
        })

class PaginaPagoSimuladaView(TemplateView):
    """
    Renderiza la página HTML donde el usuario "paga" (confirma o cancela).
    """
    template_name = 'simuladores/pagina_pago.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pago_id = self.kwargs['transaccion_id']
        pago = get_object_or_404(PagoSimulado, id=pago_id, estado='PENDIENTE')
        
        context['pago'] = pago
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

        # Enviar Webhook
        try:
            webhook_payload = {
                'transaccion_id_pasarela': str(pago.id),
                'referencia_comercio': str(pago.referencia_comercio),
                'estado': estado_final,
                'monto': str(pago.monto)
            }
            requests.post(pago.url_confirmacion, json=webhook_payload, timeout=5)
        except requests.exceptions.RequestException as e:
            print(f"ERROR: [SIMULADOR] No se pudo enviar el webhook: {e}")

        # Actualizar estado y redirigir
        pago.estado = 'PROCESADO'
        pago.save()
        
        return redirect(pago.url_retorno)
