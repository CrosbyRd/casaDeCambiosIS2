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
⚠️ *Modo pruebas (por defecto):* la validación de **estados** queda **desactivada** para
que puedas probar que:
  1) el TED valida que el código exista y sea del cliente activo, y
  2) trae el **monto correcto** según el modo.
Cuando quieras reactivar las reglas de estado, poné ``STRICT_STATE_VALIDATION=True`` abajo.
Endpoints
---------
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
        - ``monto`` (str)
        - ``moneda_origen`` / ``moneda_destino`` (códigos)
        - ``monto_origen`` / ``monto_destino`` (str)
        - ``tasa_cambio_aplicada`` (str)
   - 4xx:
     - ``ok``: ``false``
     - ``error``: Mensaje de error legible
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from usuarios.utils import get_cliente_activo
from transacciones.models import Transaccion

# ============================================================================
# FLAG DE PRUEBAS
# ----------------------------------------------------------------------------
# Dejalo en False para ignorar estados y permitir pruebas de existencia + monto.
# Cuando tu WIP de estados esté listo, ponelo en True.
# ============================================================================
STRICT_STATE_VALIDATION: bool = False


def _json_error(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": msg}, status=status)


@require_POST
def validar_transaccion(request):
    """
    Valida un código TAUSER y retorna datos mínimos para operar con el TED.
    Lógica de selección de moneda/monto:
    - ``modo='deposito'`` → usa ``moneda_origen`` / ``monto_origen``.
    - ``modo='retiro'``   → usa ``moneda_destino`` / ``monto_destino``.
    En **modo pruebas** (``STRICT_STATE_VALIDATION=False``) se omiten reglas de
    estado y tipo, validando únicamente que la transacción exista para el
    cliente activo.
    :return: :class:`django.http.JsonResponse`
    """
    # --- Parseo defensivo del body ---
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return _json_error("Cuerpo de solicitud inválido (JSON).", 400)

    codigo = (payload.get("codigo") or "").strip()
    modo = (payload.get("modo") or "").strip().lower()

    if not codigo:
        return _json_error("Debe enviar el código de operación.", 400)

    if modo not in {"retiro", "deposito"}:
        return _json_error("Modo inválido. Use 'retiro' o 'deposito'.", 400)

    # --- Cliente activo de la sesión ---
    cliente = get_cliente_activo(request)
    if not cliente:
        return _json_error("No hay un cliente activo seleccionado.", 400)

    # --- Búsqueda de transacción del cliente por código (case-insensitive) ---
    try:
        tx: Transaccion = (
            Transaccion.objects.select_related("moneda_origen", "moneda_destino")
            .get(cliente=cliente, codigo_operacion_tauser__iexact=codigo)
        )
    except Transaccion.DoesNotExist:
        return _json_error("Transacción no encontrada para el cliente activo.", 404)

    # -----------------------------------------------------------------------
    # VALIDACIÓN DE ESTADOS — OPCIONAL
    # -----------------------------------------------------------------------
    # Si STRICT_STATE_VALIDATION está en True, se aplican las reglas de estado.
    if STRICT_STATE_VALIDATION:
        estado = (tx.estado or "").lower()
        tipo = (tx.tipo_operacion or "").lower()

        if modo == "deposito":
            # Depósito se asocia a operaciones de "compra" (cliente entrega billetes)
            if tipo != "compra":
                return _json_error(
                    "Este código no corresponde a un depósito en efectivo.", 400
                )
            # Estados elegibles para permitir depósito (ajustar a tu flujo real)
            elegibles = {
                "pendiente_deposito_tauser",
                "pendiente_deposito",
                "pendiente",
            }
            if estado not in elegibles:
                # Si tu modelo tiene get_estado_display(), mostrará el label
                readable = getattr(tx, "get_estado_display", lambda: estado)()
                return _json_error(
                    f"La transacción no está habilitada para depósito "
                    f"(estado actual: {readable}).",
                    400,
                )
        else:  # modo == "retiro"
            # Retiro se asocia a operaciones de "venta" (cliente recibe billetes)
            if tipo != "venta":
                return _json_error(
                    "Este código no corresponde a un retiro en efectivo.", 400
                )
            # Para retirar solemos exigir estado "pagada"
            if estado != "pagada":
                readable = getattr(tx, "get_estado_display", lambda: estado)()
                return _json_error(
                    f"Para retirar, la transacción debe estar pagada "
                    f"(estado actual: {readable}).",
                    400,
                )

    # -----------------------------------------------------------------------
    # SELECCIÓN DE MONEDA Y MONTO (núcleo que querés probar)
    # -----------------------------------------------------------------------
    if modo == "deposito":
        moneda_codigo = tx.moneda_origen.codigo
        monto_str = str(tx.monto_origen)
    else:  # 'retiro'
        moneda_codigo = tx.moneda_destino.codigo
        monto_str = str(tx.monto_destino)

    # Armamos la respuesta estandarizada
    data = {
        "id": str(tx.id),
        "codigo": tx.codigo_operacion_tauser,
        "tipo_operacion": tx.tipo_operacion,
        "estado": getattr(tx, "estado", None),
        "moneda": moneda_codigo,
        "monto": monto_str,
        "moneda_origen": tx.moneda_origen.codigo,
        "moneda_destino": tx.moneda_destino.codigo,
        "monto_origen": str(tx.monto_origen),
        "monto_destino": str(tx.monto_destino),
        "tasa_cambio_aplicada": str(getattr(tx, "tasa_cambio_aplicada", "")),
    }
    return JsonResponse({"ok": True, "data": data}, status=200)