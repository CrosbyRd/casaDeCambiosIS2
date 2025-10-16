"""
API TED (Validación de Transacciones)
=====================================

.. module:: usuarios.ted_api
   :synopsis: Endpoints ligeros para validar transacciones en el TED.

Este módulo expone un endpoint para validar un ``codigo_operacion_tauser`` ingresado
en el TED. Verifica que la transacción pertenezca al *cliente activo* de la sesión y
devuelve la **moneda y monto** que corresponden según el **modo** solicitado:

- ``modo='retiro'``  → Se valida para entregar efectivo (usa moneda_destino / monto_destino).
- ``modo='deposito'`` → Se valida para recibir efectivo (usa moneda_origen / monto_origen).

No modifica estados de la transacción. Su objetivo es garantizar la
*coincidencia exacta* entre lo que el TED pretende operar y los datos reales
registrados en el backend.

Requisitos:
 - Usuario autenticado
 - Cliente activo seleccionado en sesión (``usuarios.utils.get_cliente_activo``)

Respuestas JSON:
 - 200 OK: ``{"ok": true, "data": { ... }} ``
 - 400/404: ``{"ok": false, "error": "..."}``

"""

from __future__ import annotations

import json
from typing import Dict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods

from usuarios.utils import get_cliente_activo
from transacciones.models import Transaccion


def _json(request: HttpRequest) -> Dict:
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


@login_required
@require_http_methods(["POST"])
def validar_transaccion(request: HttpRequest):
    """
    Valida una transacción por ``codigo_operacion_tauser`` y el ``modo`` de operación.

    .. http:post:: /usuarios/ted/api/validar/

       **Body JSON**::

          {
            "codigo": "ABCD123456",
            "modo": "retiro" | "deposito"
          }

       **Respuestas**:

       - 200 OK:
         - ``ok``: ``true``
         - ``data``: Diccionario con datos mínimos para operar
            - ``id`` (uuid)
            - ``codigo`` (str)
            - ``tipo_operacion`` (``compra`` | ``venta``)
            - ``estado`` (str)
            - ``moneda`` (código ISO de la moneda que físicamente se deposita/retira)
            - ``monto`` (str, como se guarda en modelo)
            - ``moneda_origen`` / ``moneda_destino`` (códigos)
            - ``monto_origen`` / ``monto_destino`` (str)

       - 4xx:
         - ``ok``: ``false``
         - ``error``: Mensaje de error legible

    Reglas de elegibilidad (mínimas y no destructivas):
     - ``modo='deposito'`` → buscamos **tipo_operacion = 'compra'** y estados afines a depósito:
         ``{'pendiente_deposito_tauser', 'pendiente', 'pendiente_deposito'}``
     - ``modo='retiro'`` → buscamos **tipo_operacion = 'venta'** y requerimos estado **'pagada'**.
       (Si querés permitir retiros con otro estado intermedio —p. ej. 'pendiente_retiro_ted'—,
       avisame y lo relajamos de forma controlada.)

    """
    payload = _json(request)
    codigo = (payload.get("codigo") or "").strip()
    modo = (payload.get("modo") or "").strip().lower()

    if not codigo or modo not in {"retiro", "deposito"}:
        return JsonResponse({"ok": False, "error": "Solicitud inválida."}, status=400)

    cliente = get_cliente_activo(request)
    if not cliente:
        return JsonResponse({"ok": False, "error": "No hay un cliente activo seleccionado."}, status=400)

    try:
        tx: Transaccion = Transaccion.objects.select_related("moneda_origen", "moneda_destino").get(
            cliente=cliente,
            codigo_operacion_tauser=codigo
        )
    except Transaccion.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Transacción no encontrada para el cliente activo."}, status=404)

    # Reglas suaves (no cambiamos estado, solo filtramos elegibilidad)
    estado = (tx.estado or "").lower()
    tipo = (tx.tipo_operacion or "").lower()

    if modo == "deposito":
        if tipo != "compra":
            return JsonResponse({"ok": False, "error": "Este código no corresponde a un depósito en efectivo."}, status=400)
        elegibles = {"pendiente_deposito_tauser", "pendiente", "pendiente_deposito"}
        if estado not in elegibles:
            return JsonResponse({"ok": False, "error": f"La transacción no está habilitada para depósito (estado actual: {tx.get_estado_display()})."}, status=400)
        moneda_codigo = tx.moneda_origen.codigo
        monto_str = str(tx.monto_origen)

    else:  # modo == "retiro"
        if tipo != "venta":
            return JsonResponse({"ok": False, "error": "Este código no corresponde a un retiro en efectivo."}, status=400)
        if estado != "pagada":
            return JsonResponse({"ok": False, "error": f"Para retirar, la transacción debe estar pagada (estado actual: {tx.get_estado_display()})."}, status=400)
        moneda_codigo = tx.moneda_destino.codigo
        monto_str = str(tx.monto_destino)

    data = {
        "id": str(tx.id),
        "codigo": tx.codigo_operacion_tauser,
        "tipo_operacion": tx.tipo_operacion,
        "estado": tx.estado,
        "moneda": moneda_codigo,
        "monto": monto_str,
        "moneda_origen": tx.moneda_origen.codigo,
        "moneda_destino": tx.moneda_destino.codigo,
        "monto_origen": str(tx.monto_origen),
        "monto_destino": str(tx.monto_destino),
        "tasa_cambio_aplicada": str(tx.tasa_cambio_aplicada),
    }
    return JsonResponse({"ok": True, "data": data}, status=200)
