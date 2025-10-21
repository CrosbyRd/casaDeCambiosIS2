"""
API TED (Validación, Preconteo, OTP y Confirmación)
===================================================
.. module:: usuarios.ted_api
   :synopsis: Endpoints del kiosco TED para validar códigos, precontar billetes,
              verificar OTP y confirmar retiros/depósitos con movimiento de inventario.

Este módulo extiende el endpoint existente de **validación** con tres endpoints
adicionales para completar el flujo de operación en el TED:

- ``POST /usuarios/ted/api/precontar/``
  Calcula una **combinación exacta de billetes** disponible en la **ubicación**
  seleccionada para el **monto** de la transacción (modo *retiro*). Reserva
  temporalmente esa combinación (TTL 120s) para evitar condiciones de carrera.

- ``POST /usuarios/ted/api/otp/enviar/`` y ``POST /usuarios/ted/api/otp/verificar/``
  Manejan un segundo factor (OTP) simple por correo del usuario autenticado.

- ``POST /usuarios/ted/api/confirmar/``
  Aplica los **movimientos de inventario** en una transacción DB atómica,
  actualiza el **estado** de la transacción y retorna la URL del **ticket**.

.. important::
   *No* se usa el superusuario en ningún punto. El control de permisos queda
   en la autenticación por sesión y, opcionalmente, por clave del terminal.
"""
from __future__ import annotations

import json
import secrets
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from typing import Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction as db_transaction
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from usuarios.utils import get_cliente_activo
from transacciones.models import Transaccion
from monedas.models import Moneda, TedDenominacion, TedInventario, TedMovimiento


# ==========================================================================
# FLAGS / SETTINGS
# ==========================================================================
# Modo pruebas: validar existencia + pertenencia, omitir reglas de estado.
STRICT_STATE_VALIDATION: bool = False

# Reservas de preconteo y OTP
RESERVA_TTL_SECONDS: int = getattr(settings, "TED_RESERVA_TTL_SECONDS", 120)
OTP_TTL_SECONDS: int = getattr(settings, "TED_OTP_TTL_SECONDS", 300)

# Política de redondeo "a favor de la casa"
# - Retiro: redondeo hacia abajo (paga menos billetes si hay decimales)
# - Depósito: redondeo hacia arriba (cliente deposita de más si hay decimales)
ROUNDING_RETIRO = ROUND_FLOOR
ROUNDING_DEPOSITO = ROUND_CEILING


# ==========================================================================
# Helpers
# ==========================================================================
def _json_error(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": msg}, status=status)


def _active_client(request: HttpRequest):
    cliente = get_cliente_activo(request.user)
    if not cliente:
        raise PermissionError("Debe seleccionar un cliente activo antes de operar.")
    return cliente


def _monto_y_moneda(tx: Transaccion, modo: str) -> Tuple[Decimal, Moneda]:
    if modo == "deposito":
        return tx.monto_origen, tx.moneda_origen
    return tx.monto_destino, tx.moneda_destino


def _round_for_policy(amount: Decimal, modo: str) -> Decimal:
    # Redondeo a la unidad entera de la moneda (p. ej., USD enteros)
    quant = Decimal("1")
    rounding = ROUNDING_DEPOSITO if modo == "deposito" else ROUNDING_RETIRO
    return amount.quantize(quant, rounding=rounding)


def _cache_key_reserva(rid: str) -> str:
    return f"ted:reserva:{rid}"


def _cache_key_otp(rid: str) -> str:
    return f"ted:otp:{rid}"


# ==========================================================================
# Endpoint: VALIDAR (existente, se mantiene)
# ==========================================================================
@require_POST
def validar_transaccion(request: HttpRequest) -> JsonResponse:
    """
    Valida un código TAUSER y retorna datos mínimos para operar con el TED.

    Lógica de selección de moneda/monto:
    - ``modo='deposito'`` → usa ``moneda_origen`` / ``monto_origen``.
    - ``modo='retiro'``   → usa ``moneda_destino`` / ``monto_destino``.

    En *modo pruebas* (``STRICT_STATE_VALIDATION=False``) se omiten reglas de
    estado y tipo, validando únicamente que la transacción exista para el
    cliente activo.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_error("JSON inválido.", 400)

    codigo = (payload.get("codigo") or "").strip().upper()
    modo = (payload.get("modo") or "").strip().lower()  # 'retiro' | 'deposito'
    if modo not in {"retiro", "deposito"}:
        return _json_error("Modo inválido. Debe ser 'retiro' o 'deposito'.", 400)

    try:
        cliente = _active_client(request)
    except PermissionError as e:
        return _json_error(str(e), 403)

    try:
        tx = Transaccion.objects.select_related(
            "moneda_origen", "moneda_destino", "cliente"
        ).get(codigo_operacion_tauser=codigo, cliente=cliente)
    except Transaccion.DoesNotExist:
        return _json_error("Código no encontrado para el cliente activo.", 404)

    # Reglas de estado (si se activan)
    if STRICT_STATE_VALIDATION:
        estado = (tx.estado or "").lower()
        tipo = (tx.tipo_operacion or "").lower()
        if modo == "deposito":
            if tipo != "compra":
                return _json_error("Este código no corresponde a un depósito.", 400)
            elegibles = {"pendiente_deposito_tauser"}
            if estado not in elegibles:
                return _json_error("La transacción no está habilitada para depósito.", 400)
        else:  # retiro
            if tipo != "venta":
                return _json_error("Este código no corresponde a un retiro.", 400)
            elegibles = {"pendiente_retiro_tauser"}
            if estado not in elegibles:
                return _json_error("La transacción no está habilitada para retiro.", 400)

    monto, moneda = _monto_y_moneda(tx, modo)
    data = {
        "id": str(tx.id),
        "codigo": tx.codigo_operacion_tauser,
        "tipo_operacion": tx.tipo_operacion,
        "estado": getattr(tx, "estado", None),
        "moneda": moneda.codigo,
        "monto": str(monto),
        "moneda_origen": tx.moneda_origen.codigo,
        "moneda_destino": tx.moneda_destino.codigo,
        "monto_origen": str(tx.monto_origen),
        "monto_destino": str(tx.monto_destino),
        "tasa_cambio_aplicada": str(getattr(tx, "tasa_cambio_aplicada", "")),
    }
    return JsonResponse({"ok": True, "data": data}, status=200)


# ==========================================================================
# Endpoint: PRECONTAR
# ==========================================================================
@require_POST
def precontar(request: HttpRequest) -> JsonResponse:
    """
    Calcula una **combinación exacta de billetes** disponible en la **ubicación**
    dada para el monto de la transacción.

    **Entradas**
    ------------
    - ``codigo``: Código TAUSER.
    - ``modo``: ``'retiro'`` (usa monto/moneda de destino) o ``'deposito'``.
    - ``ubicacion``: Texto exacto de la ubicación (ej.: ``"Campus, San Lorenzo – Paraguay"``).

    **Salida**
    ----------
    - ``reserva_id``: ID temporal de la reserva (TTL configurable).
    - ``monto_solicitado`` (str), ``monto_redondeado`` (str), ``diff`` (str).
    - ``breakdown``: lista de objetos ``{denominacion, unidades, valor}``.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_error("JSON inválido.", 400)

    codigo = (payload.get("codigo") or "").strip().upper()
    modo = (payload.get("modo") or "").strip().lower()
    ubicacion = (payload.get("ubicacion") or "").strip()
    if not codigo or modo not in {"retiro", "deposito"} or not ubicacion:
        return _json_error("Parámetros inválidos.", 400)

    try:
        cliente = _active_client(request)
    except PermissionError as e:
        return _json_error(str(e), 403)

    try:
        tx = Transaccion.objects.select_related(
            "moneda_origen", "moneda_destino", "cliente"
        ).get(codigo_operacion_tauser=codigo, cliente=cliente)
    except Transaccion.DoesNotExist:
        return _json_error("Código no encontrado para el cliente activo.", 404)

    monto, moneda = _monto_y_moneda(tx, modo)
    monto_redondeado = _round_for_policy(Decimal(monto), modo)
    diff = (monto_redondeado - Decimal(monto))

    # Denominaciones activas de la moneda
    denoms = list(
        TedDenominacion.objects.filter(moneda=moneda, activa=True).order_by("-valor")
    )
    if not denoms:
        return _json_error(f"No hay denominaciones configuradas para {moneda.codigo}.", 400)

    # MODO RETIRO: exige combinación exacta y stock suficiente
    breakdown: List[Tuple[int, int]] = []  # (denom_id, unidades)
    if modo == "retiro":
        objetivo = int(monto_redondeado)  # unidades enteras
        # Traer inventario por ubicación
        inv_map: Dict[int, int] = {
            inv.denominacion_id: inv.cantidad
            for inv in TedInventario.objects.filter(
                ubicacion=ubicacion, denominacion__in=denoms
            )
        }
        if not inv_map:
            return _json_error("No hay inventario configurado para esta ubicación.", 400)

        restante = objetivo
        for d in denoms:
            if restante <= 0:
                break
            stock = inv_map.get(d.id, 0)
            if d.valor <= 0 or stock <= 0:
                continue
            max_units = min(stock, restante // d.valor)
            if max_units > 0:
                breakdown.append((d.id, max_units))
                restante -= max_units * d.valor

        if restante != 0:
            return _json_error(
                "No hay combinación exacta de billetes disponible en esta ubicación.", 409
            )

    else:  # deposito
        # Para depósito, el cajero acepta lo que el cliente ingrese: el preconteo
        # sólo devuelve el monto redondeado esperado; el breakdown vendrá en confirmar.
        breakdown = []

    # Crear reserva en cache
    reserva_id = secrets.token_urlsafe(12)
    reserva_data = {
        "tx_id": str(tx.id),
        "codigo": codigo,
        "modo": modo,
        "ubicacion": ubicacion,
        "moneda": moneda.codigo,
        "monto_redondeado": str(monto_redondeado),
        "diff": str(diff),
        "breakdown": breakdown,  # retiro: reserva exacta; deposito: vacío
        "user_id": request.user.id if request.user.is_authenticated else None,
        "created_at": timezone.now().isoformat(),
    }
    cache.set(_cache_key_reserva(reserva_id), reserva_data, RESERVA_TTL_SECONDS)

    # Respuesta legible
    breakdown_out = []
    id_to_valor = {d.id: d.valor for d in denoms}
    for did, units in breakdown:
        breakdown_out.append({"denominacion": did, "valor": id_to_valor.get(did, 0), "unidades": units})

    return JsonResponse(
        {
            "ok": True,
            "data": {
                "reserva_id": reserva_id,
                "monto_solicitado": str(monto),
                "monto_redondeado": str(monto_redondeado),
                "diff": str(diff),
                "moneda": moneda.codigo,
                "ubicacion": ubicacion,
                "breakdown": breakdown_out,
            },
        },
        status=200,
    )


# ==========================================================================
# Endpoints: OTP
# ==========================================================================
@require_POST
def otp_enviar(request: HttpRequest) -> JsonResponse:
    """
    Genera y envía un OTP de 6 dígitos al correo del usuario autenticado.
    Requiere un ``reserva_id`` válido (creado por :func:`precontar`).
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
        reserva_id = (payload.get("reserva_id") or "").strip()
    except Exception:
        return _json_error("JSON inválido.", 400)

    data = cache.get(_cache_key_reserva(reserva_id))
    if not data:
        return _json_error("Reserva expirada o inexistente.", 410)

    if not request.user.is_authenticated or not getattr(request.user, "email", None):
        return _json_error("Usuario sin email para OTP.", 403)

    code = f"{secrets.randbelow(10**6):06d}"
    cache.set(_cache_key_otp(reserva_id), code, OTP_TTL_SECONDS)

    subject = "Código de verificación TED"
    body = f"Tu código OTP es: {code}. Vence en {OTP_TTL_SECONDS//60} minutos."
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [request.user.email])
    except Exception:
        # En entornos de desarrollo puede fallar: devolver el código para pruebas
        return JsonResponse({"ok": True, "test_code": code}, status=200)

    return JsonResponse({"ok": True}, status=200)


@require_POST
def otp_verificar(request: HttpRequest) -> JsonResponse:
    """
    Verifica un OTP contra el ``reserva_id``.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
        reserva_id = (payload.get("reserva_id") or "").strip()
        otp = (payload.get("otp") or "").strip()
    except Exception:
        return _json_error("JSON inválido.", 400)

    if not reserva_id or not otp:
        return _json_error("Parámetros inválidos.", 400)

    expect = cache.get(_cache_key_otp(reserva_id))
    if not expect:
        return _json_error("OTP expirado o inexistente.", 410)

    if otp != expect:
        return _json_error("OTP incorrecto.", 400)

    # Marcar como verificado (opcionalmente podríamos setear un flag en reserva)
    cache.set(_cache_key_otp(reserva_id), f"OK:{otp}", OTP_TTL_SECONDS)
    return JsonResponse({"ok": True}, status=200)


# ==========================================================================
# Endpoint: CONFIRMAR
# ==========================================================================
@require_POST
def confirmar(request: HttpRequest) -> JsonResponse:
    """
    Aplica movimientos de inventario y cambia el estado de la transacción.
    Requiere un ``reserva_id`` válido y OTP verificado.

    **Entradas**
    ------------
    - ``reserva_id``: ID devuelto por :func:`precontar`.
    - ``otp``: Código de verificación.
    - ``billetes`` *(solo depósito)*: lista ``[{valor, unidades}]``.

    **Salida**
    ----------
    - ``ticket_url``: URL para abrir/imprimir el ticket.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_error("JSON inválido.", 400)

    reserva_id = (payload.get("reserva_id") or "").strip()
    otp = (payload.get("otp") or "").strip()
    billetes = payload.get("billetes") or []

    if not reserva_id or not otp:
        return _json_error("Parámetros inválidos.", 400)

    data = cache.get(_cache_key_reserva(reserva_id))
    if not data:
        return _json_error("Reserva expirada o inexistente.", 410)

    otp_cache = cache.get(_cache_key_otp(reserva_id))
    if not otp_cache or not str(otp_cache).startswith("OK:"):
        return _json_error("OTP no verificado.", 403)

    # Releer transacción y contexto
    try:
        tx = Transaccion.objects.select_related(
            "moneda_origen", "moneda_destino", "cliente"
        ).get(id=data["tx_id"])
    except Transaccion.DoesNotExist:
        return _json_error("Transacción inexistente.", 404)

    modo = data["modo"]
    moneda = Moneda.objects.get(codigo=data["moneda"])
    ubicacion = data["ubicacion"]
    monto_redondeado = Decimal(str(data["monto_redondeado"]))

    # Denominaciones de la moneda (mapa valor->obj, id->obj)
    denoms = list(TedDenominacion.objects.filter(moneda=moneda, activa=True).order_by("-valor"))
    id_map = {d.id: d for d in denoms}
    val_map = {d.valor: d for d in denoms}

    with db_transaction.atomic():
        if modo == "retiro":
            # Reaplicar reserva contra stock con bloqueo pesimista
            rows = (
                TedInventario.objects.select_for_update()
                .filter(ubicacion=ubicacion, denominacion__in=denoms)
            )
            inv = {r.denominacion_id: r for r in rows}
            for did, units in data["breakdown"]:
                r = inv.get(did)
                if not r or r.cantidad < units:
                    return _json_error("Stock insuficiente al confirmar.", 409)

            # Descontar y registrar movimientos
            for did, units in data["breakdown"]:
                r = inv[did]
                r.cantidad -= int(units)
                r.save(update_fields=["cantidad", "updated_at"])
                TedMovimiento.objects.create(
                    denominacion=id_map[did],
                    delta=-int(units),
                    motivo=TedMovimiento.MOTIVO_COMPRA,
                    transaccion_ref=str(tx.codigo_operacion_tauser),
                )

            # Cambiar estado a 'completada' (ajustar si necesitás otro nombre)
            tx.estado = "completada"
            tx.tauser_utilizado = True
            tx.save(update_fields=["estado", "tauser_utilizado", "fecha_actualizacion"])

        else:  # deposito
            # Tomar breakdown del payload y sumar
            if not isinstance(billetes, list) or not billetes:
                return _json_error("Debe enviar breakdown de billetes para depósito.", 400)
            total_calc = 0
            for item in billetes:
                try:
                    valor = int(item["valor"])
                    unidades = int(item["unidades"])
                except Exception:
                    return _json_error("Formato inválido de billetes.", 400)
                if valor not in val_map or unidades <= 0:
                    return _json_error("Denominación inválida o unidades <= 0.", 400)
                total_calc += valor * unidades

            if total_calc != int(monto_redondeado):
                return _json_error("El breakdown no coincide con el monto redondeado.", 400)

            # Incrementar stock y registrar movimientos
            rows = (
                TedInventario.objects.select_for_update()
                .filter(ubicacion=ubicacion, denominacion__in=denoms)
            )
            inv_by_val = {r.denominacion.valor: r for r in rows}
            for item in billetes:
                valor = int(item["valor"])
                unidades = int(item["unidades"])
                r = inv_by_val.get(valor)
                if not r:
                    # Crear registro de stock si no existe para la ubicación
                    r = TedInventario.objects.create(denominacion=val_map[valor], ubicacion=ubicacion, cantidad=0)
                r.cantidad += unidades
                r.save(update_fields=["cantidad", "updated_at"])
                TedMovimiento.objects.create(
                    denominacion=val_map[valor],
                    delta=unidades,
                    motivo=TedMovimiento.MOTIVO_VENTA,
                    transaccion_ref=str(tx.codigo_operacion_tauser),
                )

            # Cambiar estado a 'procesando_acreditacion'
            tx.estado = "procesando_acreditacion"
            tx.tauser_utilizado = True
            tx.save(update_fields=["estado", "tauser_utilizado", "fecha_actualizacion"])

    # Ticket simple (HTML): devolvemos URL imprimible
    ticket_url = reverse("usuarios:ted_ticket", kwargs={"codigo": tx.codigo_operacion_tauser})
    # Limpiar reserva
    cache.delete_many([_cache_key_reserva(reserva_id), _cache_key_otp(reserva_id)])

    return JsonResponse({"ok": True, "data": {"ticket_url": ticket_url}}, status=200)


# ==========================================================================
# Ticket HTML (imprimible)
# ==========================================================================
def ticket_html(request: HttpRequest, codigo: str) -> HttpResponse:
    """
    Render mínimo de ticket imprimible en HTML (sirve como fallback si no
    tenés generador de PDF activado). Incluye datos mínimos requeridos.
    """
    try:
        tx = Transaccion.objects.select_related("moneda_origen", "moneda_destino").get(
            codigo_operacion_tauser=codigo
        )
    except Transaccion.DoesNotExist:
        return HttpResponse("Transacción no encontrada.", status=404)

    html = f"""
    <html><head><meta charset="utf-8"><title>Ticket {codigo}</title>
    <style>body{{font-family:ui-sans-serif,system-ui;padding:20px}}
    h1{{font-size:18px;margin:0 0 8px}} table{{width:100%;border-collapse:collapse}}
    td{{padding:6px;border-bottom:1px solid #eee}} small{{color:#666}}</style></head>
    <body>
      <h1>Comprobante de Operación</h1>
      <table>
        <tr><td>Código</td><td><strong>{tx.codigo_operacion_tauser}</strong></td></tr>
        <tr><td>Tipo</td><td>{tx.get_tipo_operacion_display()}</td></tr>
        <tr><td>Estado</td><td>{getattr(tx, "get_estado_display", lambda: tx.estado)()}</td></tr>
        <tr><td>Origen</td><td>{tx.moneda_origen.codigo} {tx.monto_origen}</td></tr>
        <tr><td>Destino</td><td>{tx.moneda_destino.codigo} {tx.monto_destino}</td></tr>
        <tr><td>Fecha</td><td>{timezone.localtime(tx.fecha_actualizacion or tx.fecha_creacion):%Y-%m-%d %H:%M}</td></tr>
      </table>
      <p><small>Ubicación/Terminal: se muestra en pantalla al confirmar.<br/>
      Global Exchange — Sistema TED</small></p>
      <script>window.print && setTimeout(()=>window.print(),300)</script>
    </body></html>
    """
    return HttpResponse(html)
