# ted/views.py
"""
Vistas del módulo TED (Terminal).
=================================

Este módulo contiene las vistas para operar el kiosco TED, gestionar inventario,
crear y eliminar stock, y endpoints JSON para consumo desde la terminal.

Configuración y constantes:
- TED_SERIAL: Serial del terminal.
- TED_DIRECCION: Ubicación física del terminal.
- PERM_INV_MAIN / PERM_INV_ALT1 / PERM_INV_ALT2: permisos para inventario.

Funciones auxiliares:
--------------------
- _check_inv_perm(request)
- _is_pyg(moneda)
- _monedas_operables()
- _inv_manager(for_update=False)
- _inv_filter_by_ubicacion(qs, ubicacion)
- _inv_distinct_ubicaciones()
- _inv_get_or_create(den, ubicacion, for_update=False)
- _inv_get(den, ubicacion, for_update=False)

Vistas principales:
------------------
- panel(request)
- operar(request)
- ticket_popup(request)
- cheque_mock(request)

Vistas de inventario:
--------------------
- inventario(request)
- inventario_ajustar(request, den_id)
- inventario_movimientos(request)
- crear_stock(request)
- eliminar_denominacion(request, den_id)
- eliminar_moneda(request)

Endpoints JSON:
---------------
- monedas_disponibles(request)
- ubicaciones_disponibles(request)
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, FieldError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from monedas.models import Moneda, TedDenominacion, TedInventario, TedMovimiento
from .services import get_cotizacion_vigente
from .forms import AjusteInventarioForm

# ──────────────────────────────────────────────────────────────────────────────
# Config del equipo (mock por ahora; tu serie real puede venir de tu modelo)
TED_SERIAL = "TED-AGSL-0001"
TED_DIRECCION = "Campus, San Lorenzo – Paraguay"
# ──────────────────────────────────────────────────────────────────────────────

# Permisos compatibles para Inventario TED (acepta cualquiera de estos)
PERM_INV_MAIN = "monedas.puede_gestionar_inventario"
PERM_INV_ALT1 = "monedas.access_ted_inventory"
PERM_INV_ALT2 = "ted.puede_gestionar_inventario"


def _check_inv_perm(request):
    """
    Verifica si el usuario tiene cualquiera de los permisos de inventario.
    Si no, muestra mensaje y redirige a 'home'.
    Devuelve None si OK; un redirect si NO OK.
    """
    ok = (
        request.user.has_perm(PERM_INV_MAIN) or
        request.user.has_perm(PERM_INV_ALT1) or
        request.user.has_perm(PERM_INV_ALT2)
    )
    if ok:
        return None
    messages.error(request, "No tenés permisos para ver/editar el inventario TED.")
    return redirect("home")

def _is_pyg(moneda: Moneda) -> bool:
    return moneda.codigo.upper() == "PYG"


def _monedas_operables():
    base = Moneda.objects.exclude(codigo__iexact="PYG").order_by("codigo")
    marcadas = base.filter(admite_terminal=True)
    return marcadas if marcadas.exists() else base


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de inventario (compatibles con modelos con/sin `ubicacion`)
# ──────────────────────────────────────────────────────────────────────────────

def _inv_manager(for_update: bool = False):
    return TedInventario.objects.select_for_update() if for_update else TedInventario.objects


def _inv_filter_by_ubicacion(qs, ubicacion: str):
    try:
        return qs.filter(ubicacion=ubicacion)
    except FieldError:
        return qs


def _inv_distinct_ubicaciones():
    try:
        qs = (TedInventario.objects.values_list("ubicacion", flat=True)
              .distinct().order_by("ubicacion"))
        vals = [u for u in qs if (u or "").strip()]
        return vals or [TED_DIRECCION]
    except FieldError:
        return [TED_DIRECCION]


def _inv_get_or_create(den, ubicacion: str, for_update: bool = False):
    mgr = _inv_manager(for_update)
    try:
        return mgr.get_or_create(denominacion=den, ubicacion=ubicacion, defaults={"cantidad": 0})
    except FieldError:
        return mgr.get_or_create(denominacion=den, defaults={"cantidad": 0})


def _inv_get(den, ubicacion: str, for_update: bool = False):
    mgr = _inv_manager(for_update).filter(denominacion=den)
    qs = _inv_filter_by_ubicacion(mgr, ubicacion)
    return qs.first()


# =========================
# Sección OPERATIVA
# =========================

@login_required
@permission_required("ted.puede_operar_terminal", raise_exception=True)
def panel(request):
    """
    Vista principal del kiosco TED.

    Permisos:
        - Login obligatorio.
        - Permiso 'ted.puede_operar_terminal'.

    Funcionalidad:
        - Muestra las monedas disponibles para operar (excluye PYG).

    Retorna:
        - Render del template "ted/panel.html" con las monedas operables.
    """
    monedas = _monedas_operables()
    return render(request, "ted/panel.html", {"monedas": monedas})


@login_required
@permission_required("ted.puede_operar_terminal", raise_exception=True)
@transaction.atomic
def operar(request):
    """
    Ejecuta una operación COMPRA o VENTA en el kiosco TED.

    Flujo:
        - COMPRA: el cliente compra moneda extranjera, se descuenta del inventario,
                  se cobra en PYG usando tasa de VENTA.
        - VENTA: el cliente vende moneda extranjera, se incrementa inventario,
                 se paga en PYG usando tasa de COMPRA.

    Parámetros:
        - GET/POST 'moneda': id de la moneda a operar.
        - POST 'operacion': 'COMPRA' o 'VENTA'.
        - POST 'den_<id>': cantidades por denominación.
    
    Validaciones:
        - Verifica existencia de moneda y cotización vigente.
        - Verifica cantidades positivas y stock suficiente (en COMPRA).
    
    Postcondiciones:
        - Actualiza inventario TED.
        - Crea movimientos TedMovimiento.
        - Guarda ticket en sesión.
    
    Retorna:
        - Redirección a 'ticket_popup' si POST exitoso.
        - Render de "ted/operar.html" si GET o errores.
    
    COMPRA = el cliente compra extranjera  -> retiramos billetes -> cobramos PYG (usa tasa VENTA)
    VENTA  = el cliente vende extranjera   -> depositan billetes -> pagamos PYG (usa tasa COMPRA)
    """
    monedas = _monedas_operables()
    moneda_id = request.GET.get("moneda") or request.POST.get("moneda")
    operacion = request.POST.get("operacion") if request.method == "POST" else "COMPRA"
    ubicacion = TED_DIRECCION  # este terminal físico (mock)

    moneda = None
    denominaciones = []
    cotiz = None

    if moneda_id:
        try:
            moneda = Moneda.objects.get(id=moneda_id)
            if _is_pyg(moneda):
                messages.error(request, "Solo se permiten operaciones PYG ↔ Moneda extranjera.")
                return redirect("admin_panel:ted:panel")
            denominaciones = TedDenominacion.objects.filter(moneda=moneda, activa=True).order_by("valor")
            cotiz = get_cotizacion_vigente(moneda)
        except Moneda.DoesNotExist:
            moneda = None

    if request.method == "POST":
        if not moneda:
            messages.error(request, "Seleccione una moneda.")
            return redirect("admin_panel:ted:operar")

        if not cotiz or not cotiz.get("vigente"):
            messages.error(request, "No hay una cotización vigente (≤ 15 min). Actualiza las tasas.")
            return redirect(f"{request.path}?moneda={moneda.id}")

        # Parseo de cantidades por denominación
        cantidades = []
        total_ext = Decimal("0")
        for den in denominaciones:
            key = f"den_{den.id}"
            try:
                q = int(request.POST.get(key, "0") or "0")
                if q < 0:
                    raise ValueError
            except ValueError:
                messages.error(request, "Cantidades inválidas.")
                return redirect(f"{request.path}?moneda={moneda.id}")

            if q > 0:
                cantidades.append((den, q))
                total_ext += Decimal(den.valor) * q

        if total_ext <= 0:
            messages.error(request, "Ingrese al menos una denominación.")
            return redirect(f"{request.path}?moneda={moneda.id}")

        # Determina tasa y signo de inventario
        if operacion == "COMPRA":
            tasa = cotiz["venta"]   # vendemos extranjera → cobramos en PYG
            motivo = TedMovimiento.MOTIVO_COMPRA
            signo = -1              # retiramos billetes (descarga stock)
        else:
            operacion = "VENTA"
            tasa = cotiz["compra"]  # compramos extranjera → pagamos en PYG
            motivo = TedMovimiento.MOTIVO_VENTA
            signo = +1              # depositan billetes (aumenta stock)

        total_pyg = (total_ext * tasa).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # Validaciones de stock en COMPRA
        if signo < 0:
            for den, q in cantidades:
                inv, _ = _inv_get_or_create(den, ubicacion, for_update=True)
                if inv.cantidad < q:
                    messages.error(
                        request,
                        f"Stock insuficiente para {den.valor} {moneda.codigo}. Disponible: {inv.cantidad}."
                    )
                    return redirect(f"{request.path}?moneda={moneda.id}")

        # Aplica movimientos e inventario
        for den, q in cantidades:
            inv, _ = _inv_get_or_create(den, ubicacion, for_update=True)
            inv.cantidad = inv.cantidad + signo * q
            inv.save()

            TedMovimiento.objects.create(
                denominacion=den,
                delta=signo * q,
                motivo=motivo,
                creado_por=request.user,
                transaccion_ref="",  # mock
            )

        # Guarda ticket en sesión
        request.session["ted_ticket"] = {
            "fecha": timezone.now().isoformat(),
            "operacion": operacion,
            "moneda": moneda.codigo,
            "tasa_aplicada": str(tasa),
            "total_extranjera": str(total_ext),
            "total_pyg": str(total_pyg),
            "detalles": [{"valor": den.valor, "cantidad": q} for den, q in cantidades],
        }

        return redirect("admin_panel:ted:ticket")

    ctx = {
        "monedas": monedas,
        "moneda": moneda,
        "denominaciones": denominaciones,
        "cotiz": cotiz,
        "operacion": operacion,
    }
    return render(request, "ted/operar.html", ctx)


@login_required
@permission_required("ted.puede_operar_terminal", raise_exception=True)
def ticket_popup(request):
    """
    Muestra el ticket de la última operación TED guardado en sesión.

    Permisos:
        - Login obligatorio.
        - Permiso 'ted.puede_operar_terminal'.

    Flujo:
        - Si no hay ticket en sesión, redirige con mensaje de error.
        - Si existe, renderiza el template 'ted/ticket_popup.html'.

    Parámetros:
        - Ninguno.

    Retorna:
        - Render de ticket_popup con detalles de la operación.
    """
    ticket = request.session.get("ted_ticket")
    if not ticket:
        messages.error(request, "Ticket no disponible o expirado.")
        return redirect("admin_panel:ted:panel")
    return render(request, "ted/ticket_popup.html", {"t": ticket})


@login_required
@permission_required("ted.puede_operar_terminal", raise_exception=True)
def cheque_mock(request):
    """
    Muestra el ticket de la última operación TED guardado en sesión.

    Permisos:
        - Login obligatorio.
        - Permiso 'ted.puede_operar_terminal'.

    Flujo:
        - Si no hay ticket en sesión, redirige con mensaje de error.
        - Si existe, renderiza el template 'ted/ticket_popup.html'.

    Parámetros:
        - Ninguno.

    Retorna:
        - Render de ticket_popup con detalles de la operación.
    """
    monedas = _monedas_operables()
    return render(request, "ted/cheque_mock.html", {"monedas": monedas})


# =============================
# Sección INVENTARIO (ADMIN)
# =============================

@login_required
def inventario(request):
    """
    Vista para mostrar el inventario completo de TED.

    Permite:
    - Filtrar por ubicación (una específica o todas)
    - Filtrar por moneda
    - Mostrar todas las denominaciones activas y sus cantidades
    - Mostrar íconos/emojis de monedas
    - Agrupar denominaciones por moneda y por ubicación
    - Proveer contexto para botones de creación, ajuste o eliminación

    Flujo general:
    ----------------
    1. Verifica permisos TED mediante `_check_inv_perm`.
    2. Obtiene filtro de ubicación y todas las ubicaciones disponibles.
    3. Construye queryset de denominaciones activas y ordena por moneda y valor.
    4. Filtra por moneda si se especifica en GET.
    5. Construye queryset base de inventario (filtrando por denominaciones activas
       y monedas visibles en terminal) y aplica filtro de ubicación si existe.
    6. Genera lista de monedas presentes en el inventario para mostrar en filtros.
    7. Asigna un emoji a cada moneda para visualización, usando campo `emoji` o
       mapeo por código.
    8. Agrupa el inventario:
       - Si hay filtro de ubicación: muestra un grupo por moneda con items (denominación + stock)
       - Si no hay filtro de ubicación: muestra todas las ubicaciones, creando secciones
         por moneda y por ubicación
    9. Prepara contexto con serial TED, grupos, ubicaciones y filtros aplicados.
    10. Renderiza plantilla `admin_inventario.html`.

    Notas de diseño:
    ----------------
    - `_inv_filter_by_ubicacion` centraliza la lógica de filtrado por ubicación.
    - Agrupamiento por moneda facilita la visualización en tablas o secciones.
    - Se maneja caso FieldError para modelos sin campo 'ubicacion'.
    - Se distinguen filtros aplicados para marcar visualmente en la interfaz.
    - La función no modifica datos, solo construye el contexto para renderizar.

    :param request: HttpRequest
    :return: HttpResponse renderizado con contexto de inventario TED
    """
    resp = _check_inv_perm(request)
    if resp:
        return resp
    
    ubicacion_sel = (request.GET.get("ubicacion") or "").strip() or None  # None = sin filtro
    ubicaciones_todas = _inv_distinct_ubicaciones()

    den_qs = (
        TedDenominacion.objects
        .filter(activa=True, moneda__admite_terminal=True)
        .select_related("moneda")
        .order_by("moneda__codigo", "valor")
    )

        # --- Filtro por moneda ---
    moneda_sel = (request.GET.get("moneda") or "").strip() or None

    # Monedas que existen en inventario (respetando ubicación si se eligió)
    inv_qs_base = TedInventario.objects.filter(
        denominacion__activa=True,
        denominacion__moneda__admite_terminal=True,
    )
    if ubicacion_sel:
        inv_qs_base = _inv_filter_by_ubicacion(inv_qs_base, ubicacion_sel)

    mon_ids = inv_qs_base.values_list("denominacion__moneda_id", flat=True).distinct()
    monedas_filtro = list(Moneda.objects.filter(id__in=mon_ids).order_by("codigo"))

    # Emoji display: usa campo 'emoji' si existe; si no, mapea por código
    EMOJI_MAP = {
        "USD": "🇺🇸", "EUR": "🇪🇺", "BRL": "🇧🇷", "ARS": "🇦🇷",
        "CLP": "🇨🇱", "PEN": "🇵🇪", "UYU": "🇺🇾", "JPY": "🇯🇵", "GBP": "🇬🇧",
    }
    for m in monedas_filtro:
        setattr(m, "emoji_display", getattr(m, "emoji", EMOJI_MAP.get(m.codigo.upper(), "💱")))

    # Si eligieron una moneda, filtra las denominaciones
    if moneda_sel:
        den_qs = den_qs.filter(moneda__codigo__iexact=moneda_sel)

    grupos = []

    if ubicacion_sel:
        inv_qs = TedInventario.objects.filter(denominacion__in=den_qs)
        inv_qs = _inv_filter_by_ubicacion(inv_qs, ubicacion_sel)
        inv_map = {i.denominacion_id: i for i in inv_qs}

        actual = None
        for den in den_qs:
            if not actual or actual["moneda"].id != den.moneda_id:
                actual = {"moneda": den.moneda, "items": []}
                grupos.append(actual)
            stock = inv_map.get(den.id)
            actual["items"].append({"den": den, "stock": stock.cantidad if stock else 0})

        direccion_label = ubicacion_sel
        filtro_aplicado = True
    else:
        # Todas las ubicaciones
        try:
            rows = (TedInventario.objects.filter(denominacion__in=den_qs)
                    .values("denominacion_id", "ubicacion", "cantidad"))
            inv_por_ubi = {}
            for r in rows:
                u = r.get("ubicacion") or TED_DIRECCION
                inv_por_ubi.setdefault(u, {})[r["denominacion_id"]] = r["cantidad"]
        except FieldError:
            inv_map = {i.denominacion_id: i.cantidad for i in TedInventario.objects.filter(denominacion__in=den_qs)}
            inv_por_ubi = {TED_DIRECCION: inv_map}

        ubic_list = sorted(inv_por_ubi.keys())
        moneda_denominaciones = {}
        for den in den_qs:
            moneda_denominaciones.setdefault(den.moneda_id, []).append(den)

        for moneda_id, dens in moneda_denominaciones.items():
            moneda = dens[0].moneda
            grupo = {"moneda": moneda, "secciones": []}
            for ubic in ubic_list:
                mapa = inv_por_ubi.get(ubic, {})
                items = [{"den": den, "stock": mapa.get(den.id, 0)} for den in dens]
                grupo["secciones"].append({"ubicacion": ubic, "items": items})
            grupos.append(grupo)

        direccion_label = "Todas las ubicaciones"
        filtro_aplicado = False

    ctx = {
        "serial": TED_SERIAL,
        "direccion": direccion_label,
        "ubicaciones": ubicaciones_todas,
        "filtro_ubicacion": ubicacion_sel,
        "filtro_aplicado": filtro_aplicado,
        "grupos": grupos,
        "monedas": monedas_filtro,
        "filtro_moneda": moneda_sel,
    }
    return render(request, "ted/admin_inventario.html", ctx)


@login_required
@transaction.atomic
def inventario_ajustar(request, den_id: int):
    """
    Ajuste manual de stock de una denominación TED.

    Flujo:
    1. Obtiene la denominación por den_id.
    2. Inicializa AjusteInventarioForm con cantidad actual.
    3. Si POST:
       - Valida la cantidad ingresada
       - Actualiza inventario
       - Registra movimiento en TedMovimiento
       - Muestra mensaje de éxito
    4. Si GET, muestra formulario con cantidad actual

    :param request: HttpRequest
    :param den_id: int
    :return: Render de 'ted/admin_ajustar.html' o redirect
    """
    resp = _check_inv_perm(request)
    if resp:
        return resp
    
    ubicacion = request.GET.get("ubicacion") or TED_DIRECCION

    den = get_object_or_404(
        TedDenominacion.objects.select_related("moneda"),
        pk=den_id, activa=True
    )
    inv, _ = _inv_get_or_create(den, ubicacion, for_update=True)

    if request.method == "POST":
        form = AjusteInventarioForm(request.POST)
        if form.is_valid():
            delta = form.cleaned_data["delta"]
            motivo = form.cleaned_data["motivo"]
            comentario = form.cleaned_data.get("comentario") or ""

            nuevo = inv.cantidad + delta
            if nuevo < 0:
                messages.error(request, "El ajuste dejaría el stock negativo.")
            else:
                inv.cantidad = nuevo
                inv.save()

                TedMovimiento.objects.create(
                    denominacion=den,
                    delta=delta,
                    motivo=motivo,
                    creado_por=request.user,
                    transaccion_ref=comentario[:64],
                )
                messages.success(request, "Ajuste aplicado correctamente.")
                if request.GET.get("ubicacion"):
                    return redirect(f"{request.build_absolute_uri('/admin_panel/ted/inventario/')}?ubicacion={ubicacion}")
                return redirect("/admin_panel/ted/inventario/")
    else:
        form = AjusteInventarioForm(initial={"delta": 0})

    return render(
        request,
        "ted/admin_ajustar.html",
        {"den": den, "inv": inv, "serial": TED_SERIAL, "direccion": ubicacion, "form": form},
    )


@login_required
def inventario_movimientos(request):
    """
    Crear nueva denominación en inventario TED.

    Flujo:
    1. Formulario de denominación y cantidad inicial
    2. Validación de datos
    3. Guardado en TedDenominacion y TedInventario
    4. Registro inicial en TedMovimiento
    5. Mensaje de éxito y redirect al inventario

    :param request: HttpRequest
    :return: Render de 'ted/admin_crear.html' o redirect
    """
    resp = _check_inv_perm(request)
    if resp:
        return resp

    movs = (
        TedMovimiento.objects
        .select_related("denominacion", "denominacion__moneda", "creado_por")
        .order_by("-created_at")[:200]
    )
    return render(
        request,
        "ted/admin_movimientos.html",
        {"movs": movs, "serial": TED_SERIAL, "direccion": TED_DIRECCION},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Crear stock (con modo prefill)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@transaction.atomic
def crear_stock(request):
    """
    Vista para crear nuevas denominaciones y stock TED.

    Esta función permite agregar nuevas denominaciones a una moneda específica
    en una ubicación determinada. Incluye soporte para prefill de moneda y 
    ubicación, validaciones de valores y stock, y registro automático de 
    movimientos en TedMovimiento.

    Flujo general:
    ----------------
    1. Verifica permisos de inventario TED mediante `_check_inv_perm`.
    2. Obtiene listado de monedas disponibles (excluye PYG) para mostrar en formulario.
    3. Determina prefill de moneda y ubicación a partir de GET o POST.
    4. Si existe prefill, busca denominaciones existentes y construye listado
       de filas existentes con cantidad para mostrar en el formulario.
    5. GET: Renderiza la plantilla `admin_crear_stock.html` con información
       de monedas, prefill, filas existentes y serial TED.
    6. POST: Procesa los datos enviados por formulario:
       - Valida que se haya seleccionado una moneda.
       - Obtiene valores y stocks de las denominaciones a crear.
       - Valida que los valores sean enteros positivos y stocks >= 0.
       - Detecta denominaciones repetidas en la misma carga.
       - Detecta choque con denominaciones ya existentes en la ubicación.
       - Crea denominaciones nuevas si no existen o reactiva existentes inactivas.
       - Crea o actualiza inventario en la ubicación.
       - Registra movimientos de ajuste en TedMovimiento.
       - Marca la moneda como visible en terminal si no lo estaba.
       - Muestra mensaje de éxito y redirige al inventario.

    Notas de diseño:
    ----------------
    - Uso de `@transaction.atomic` asegura consistencia entre creación de 
      denominaciones, inventario y movimientos.
    - Se implementa prefill dinámico para mejorar UX del administrador.
    - Validaciones estrictas de valores y stock previenen errores de inventario.
    - Movimientos TED se registran solo si cantidad != 0 y existe MOTIVO_AJUSTE.
    - La función distingue entre GET (renderizar formulario) y POST (persistir datos).

    :param request: HttpRequest
    :return: HttpResponse renderizado o redirect a inventario TED
    """
    resp = _check_inv_perm(request)
    if resp:
        return resp
    
    monedas = Moneda.objects.exclude(codigo__iexact="PYG").order_by("codigo")

    prefill_moneda_id = request.GET.get("moneda") or request.POST.get("moneda_locked")
    prefill_ubic = (request.GET.get("ubicacion") or request.POST.get("ubicacion_locked") or "").strip()

    moneda_sel = None
    existentes = []
    if prefill_moneda_id:
        try:
            moneda_sel = Moneda.objects.get(pk=prefill_moneda_id)
        except Moneda.DoesNotExist:
            moneda_sel = None

    if moneda_sel and prefill_ubic:
        den_ids = list(
            TedInventario.objects.filter(ubicacion=prefill_ubic, denominacion__moneda=moneda_sel)
            .values_list("denominacion_id", flat=True)
        )
        if den_ids:
            den_qs = TedDenominacion.objects.filter(pk__in=den_ids).order_by("valor")
            inv_map = {
                i.denominacion_id: i.cantidad
                for i in TedInventario.objects.filter(ubicacion=prefill_ubic, denominacion_id__in=den_ids)
            }
            existentes = [(den.valor, inv_map.get(den.id, 0)) for den in den_qs]

    if request.method == "POST":
        moneda_id = request.POST.get("moneda") or prefill_moneda_id
        ubicacion = (request.POST.get("ubicacion") or prefill_ubic or "").strip() or TED_DIRECCION

        if not moneda_id:
            messages.error(request, "Seleccione una moneda.")
            return render(request, "ted/admin_crear_stock.html", {
                "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION,
                "prefill": bool(prefill_moneda_id and prefill_ubic),
                "moneda_sel": moneda_sel, "ubicacion_sel": prefill_ubic,
                "existentes": existentes, "new_rows": []
            })

        moneda = get_object_or_404(Moneda, pk=moneda_id)

        vals = request.POST.getlist("den_valor[]")
        stocks = request.POST.getlist("den_stock[]")

        filas = []
        for v, s in zip(vals, stocks):
            if (v or "").strip() == "" and (s or "").strip() == "":
                continue
            try:
                valor = int(Decimal(v))
                if valor <= 0:
                    raise InvalidOperation
            except Exception:
                messages.error(request, f"Valor de denominación inválido: {v!r}")
                return render(request, "ted/admin_crear_stock.html", {
                    "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION,
                    "prefill": bool(prefill_moneda_id and prefill_ubic),
                    "moneda_sel": moneda_sel, "ubicacion_sel": prefill_ubic,
                    "existentes": existentes, "new_rows": list(zip(vals, stocks))
                })
            try:
                cantidad = int(s)
                if cantidad < 0:
                    raise ValueError
            except Exception:
                messages.error(request, f"Stock inválido para la denominación {v}.")
                return render(request, "ted/admin_crear_stock.html", {
                    "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION,
                    "prefill": bool(prefill_moneda_id and prefill_ubic),
                    "moneda_sel": moneda_sel, "ubicacion_sel": prefill_ubic,
                    "existentes": existentes, "new_rows": list(zip(vals, stocks))
                })
            filas.append((valor, cantidad))

        # Validaciones
        seen = set()
        dupe_local = [v for v in filas if (v in seen or seen.add(v))]
        if dupe_local:
            messages.error(request, "Hay denominaciones repetidas en las filas nuevas.")
            return render(request, "ted/admin_crear_stock.html", {
                "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION,
                "prefill": bool(prefill_moneda_id and prefill_ubic),
                "moneda_sel": moneda_sel, "ubicacion_sel": prefill_ubic,
                "existentes": existentes, "new_rows": list(zip(vals, stocks))
            })

        existentes_set = set(v for v, _ in existentes)
        choque = [v for v, _ in filas if v in existentes_set]
        if choque:
            mensajes = ", ".join(str(v) for v in sorted(set(choque)))
            messages.error(request, f"Estas denominaciones ya existen en esta ubicación: {mensajes}.")
            return render(request, "ted/admin_crear_stock.html", {
                "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION,
                "prefill": bool(prefill_moneda_id and prefill_ubic),
                "moneda_sel": moneda_sel, "ubicacion_sel": prefill_ubic,
                "existentes": existentes, "new_rows": list(zip(vals, stocks))
            })

        # Persistencia
        for valor, cantidad in filas:
            den, _ = TedDenominacion.objects.get_or_create(
                moneda=moneda, valor=valor, defaults={"activa": True}
            )
            if not den.activa:
                den.activa = True
                den.save(update_fields=["activa"])

            inv, created = _inv_get_or_create(den, ubicacion, for_update=True)
            if not created:
                messages.error(request, f"La denominación {valor} ya existe en {ubicacion}.")
                return render(request, "ted/admin_crear_stock.html", {
                    "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION,
                    "prefill": bool(prefill_moneda_id and prefill_ubic),
                    "moneda_sel": moneda_sel, "ubicacion_sel": prefill_ubic,
                    "existentes": existentes, "new_rows": list(zip(vals, stocks))
                })
            inv.cantidad = cantidad
            inv.save()

            motivo_ajuste = getattr(TedMovimiento, "MOTIVO_AJUSTE", None)
            if motivo_ajuste is not None and cantidad != 0:
                TedMovimiento.objects.create(
                    denominacion=den,
                    delta=cantidad,
                    motivo=motivo_ajuste,
                    creado_por=request.user,
                    transaccion_ref=f"CREAR_STOCK[{ubicacion}]",
                )

        if not moneda.admite_terminal:
            moneda.admite_terminal = True
            moneda.save(update_fields=["admite_terminal"])

        messages.success(request, "Denominaciones agregadas correctamente.")
        if prefill_moneda_id and prefill_ubic:
            return redirect(f"{request.build_absolute_uri('/admin_panel/ted/inventario/')}?ubicacion={prefill_ubic}")
        return redirect("/admin_panel/ted/inventario/")

    return render(
        request,
        "ted/admin_crear_stock.html",
        {
            "monedas": monedas,
            "serial": TED_SERIAL,
            "direccion": TED_DIRECCION,
            "prefill": bool(moneda_sel and prefill_ubic),
            "moneda_sel": moneda_sel,
            "ubicacion_sel": prefill_ubic,
            "existentes": existentes,
            "new_rows": [],
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Eliminar denominación (confirmación + ejecución)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@transaction.atomic
@login_required
@transaction.atomic
def eliminar_denominacion(request, den_id: int):
    """
    Elimina una denominación específica del inventario TED.

    Flujo completo:
    ----------------
    1. Verifica que el usuario tenga permisos para gestión de inventario TED.
    2. Obtiene la denominación a eliminar mediante `den_id`.
    3. Construye un resumen global de stock de esta denominación en todas las ubicaciones.
       - Esto permite mostrar información en la confirmación GET.
       - Maneja errores si no existen campos de ubicación.
    4. GET: muestra la pantalla de confirmación con resumen global.
    5. POST: realiza la eliminación:
       - `scope="global"`: elimina la denominación de todas las ubicaciones y desactiva la denominación.
       - Por defecto (`scope="ubicacion"`): elimina la denominación solo de la ubicación especificada.
    6. Registra ajustes en `TedMovimiento` para mantener historial.
    7. Muestra mensajes informativos o de éxito según resultado.
    8. Redirige al inventario TED, respetando filtros de ubicación.

    Notas de diseño:
    ----------------
    - Uso de `@transaction.atomic` para garantizar consistencia de inventario y movimientos.
    - La denominación nunca se borra completamente de la base; se desactiva (`activa=False`) para preservar historial.
    - Los movimientos de ajuste se registran solo si existe cantidad distinta de cero y `MOTIVO_AJUSTE` definido.
    - El filtrado de ubicación se hace dinámico según GET o POST; si no se indica, se toma la ubicación principal `TED_DIRECCION`.

    :param request: HttpRequest
    :param den_id: int, ID de la denominación a eliminar
    :return: HttpResponseRedirect al inventario TED o render de confirmación
    """
    resp = _check_inv_perm(request)
    if resp:
        return resp

    ubicacion = request.GET.get("ubicacion") or request.POST.get("ubicacion") or TED_DIRECCION
    den = get_object_or_404(TedDenominacion.objects.select_related("moneda"), pk=den_id)

    # Para el resumen global en la pantalla GET
    try:
        inv_rows = (TedInventario.objects
                    .filter(denominacion=den)
                    .values("ubicacion", "cantidad"))
        resumen_global = [
            {"ubicacion": (r.get("ubicacion") or TED_DIRECCION), "cantidad": r["cantidad"]}
            for r in inv_rows
        ]
    except FieldError:
        fila = TedInventario.objects.filter(denominacion=den).first()
        resumen_global = [{"ubicacion": TED_DIRECCION, "cantidad": getattr(fila, "cantidad", 0)}] if fila else []
    total_global = sum(r["cantidad"] for r in resumen_global)

    if request.method == "GET":
        inv = _inv_get(den, ubicacion, for_update=False)
        return render(
            request,
            "ted/admin_eliminar_den.html",
            {
                "den": den,
                "inv": inv,
                "serial": TED_SERIAL,
                "ubicacion": ubicacion,
                "resumen_global": resumen_global,
                "total_global": total_global,
            },
        )

    # POST
    scope = (request.POST.get("scope") or "ubicacion").lower()
    motivo_ajuste = getattr(TedMovimiento, "MOTIVO_AJUSTE", None)

    if scope == "global":
        # 1) Ajustar a 0 y borrar TODAS las filas de inventario de esta denominación
        inv_qs = _inv_manager(for_update=True).filter(denominacion=den)
        for inv in inv_qs:
            if motivo_ajuste is not None and inv.cantidad and inv.cantidad != 0:
                try:
                    TedMovimiento.objects.create(
                        denominacion=den,
                        delta=-inv.cantidad,
                        motivo=motivo_ajuste,
                        creado_por=request.user,
                        transaccion_ref=f"ELIMINAR_DENOMINACION_GLOBAL[{den.moneda.codigo}]",
                    )
                except Exception:
                    pass
            inv.cantidad = 0
            inv.save()
            # Borramos la fila de inventario (tenga o no campo ubicacion)
            inv.delete()

        # 2) Desactivar la denominación (preserva historial de movimientos)
        if den.activa:
            den.activa = False
            den.save(update_fields=["activa"])

        messages.success(
            request,
            f"Se eliminó la denominación {den.moneda.codigo} {den.valor} en TODAS las ubicaciones y fue desactivada."
        )
        return redirect("admin_panel:ted:inventario")

    # --- scope por defecto: solo esta ubicación ---
    inv = _inv_get(den, ubicacion, for_update=True)
    if inv:
        if inv.cantidad != 0:
            delta = -inv.cantidad
            inv.cantidad = 0
            inv.save()
            if motivo_ajuste is not None:
                TedMovimiento.objects.create(
                    denominacion=den,
                    delta=delta,
                    motivo=motivo_ajuste,
                    creado_por=request.user,
                    transaccion_ref=f"ELIMINAR_DENOMINACION[{ubicacion}]",
                )
        # Si manejás ubicaciones, borramos la fila de inventario
        inv.delete()
        messages.success(request, "Denominación eliminada para esta ubicación.")
    else:
        messages.info(request, "La denominación no tiene inventario en esta ubicación.")

    # Volver respetando el filtro de ubicación si vino en la URL
    if request.GET.get("ubicacion") or request.POST.get("ubicacion"):
        return redirect(f"{request.build_absolute_uri('/admin_panel/ted/inventario/')}?ubicacion={ubicacion}")
    return redirect("/admin_panel/ted/inventario/")

@login_required
@transaction.atomic
def eliminar_moneda(request, moneda_id: int):
    """
    Elimina COMPLETAMENTE una moneda del TED:
      - Borra TODO el inventario (todas las ubicaciones) de todas sus denominaciones.
      - Registra movimientos de ajuste a 0 por cada fila de inventario eliminada.
      - Desactiva las denominaciones (activa=False) para preservar el historial.
      - Desmarca la moneda para el terminal (admite_terminal=False) para que desaparezca de filtros y del kiosco.
    No toca PYG.
    
    Elimina completamente una moneda del TED, incluyendo todas sus denominaciones
    y movimientos de inventario, preservando historial.

    Flujo completo:
    ----------------
    1. Verifica permisos de inventario TED.
    2. Recupera la moneda por ID. Nunca permite PYG.
    3. Recupera todas las denominaciones de la moneda.
    4. GET: pantalla de confirmación con:
       - Cantidad de denominaciones
       - Total de filas de inventario
       - Ubicaciones afectadas
    5. POST: ejecutar eliminación:
       - Ajusta inventario a 0 y registra movimientos para cada fila de inventario.
       - Desactiva denominaciones (`activa=False`) para preservar historial.
       - Desmarca moneda para el terminal (`admite_terminal=False`) para ocultarla en filtros.
    6. Muestra mensaje de éxito.
    7. Redirige a inventario TED.

    Notas de diseño:
    ----------------
    - Uso de `@transaction.atomic` para consistencia de inventario y movimientos.
    - Movimientos se crean solo si cantidad > 0 y `MOTIVO_AJUSTE` definido.
    - La moneda nunca se borra de la base para preservar integridad referencial; solo se oculta del terminal.
    - Bloqueo de filas (`select_for_update`) para evitar race conditions en operaciones concurrentes.

    :param request: HttpRequest
    :param moneda_id: int, ID de la moneda a eliminar
    :return: HttpResponseRedirect al inventario TED o render de confirmación
    """
    resp = _check_inv_perm(request)
    if resp:
        return resp

    moneda = get_object_or_404(Moneda, pk=moneda_id)

    # Nunca permitir acciones sobre PYG
    if _is_pyg(moneda):
        messages.error(request, "No se puede eliminar PYG del TED.")
        return redirect("admin_panel:ted:inventario")

    # Denominaciones de esta moneda
    den_qs = TedDenominacion.objects.filter(moneda=moneda)

    # GET: pantalla de confirmación
    if request.method == "GET":
        # Conteos para mostrar en la confirmación
        try:
            inv_rows = (TedInventario.objects
                        .filter(denominacion__in=den_qs)
                        .values("ubicacion").distinct())
            ubicaciones = sorted([(r.get("ubicacion") or TED_DIRECCION) for r in inv_rows])
        except FieldError:
            # Si el modelo no tiene 'ubicacion'
            ubicaciones = [TED_DIRECCION] if TedInventario.objects.filter(denominacion__in=den_qs).exists() else []

        total_denom = den_qs.count()
        total_filas_inv = TedInventario.objects.filter(denominacion__in=den_qs).count()

        return render(
            request,
            "ted/admin_eliminar_moneda.html",
            {
                "serial": TED_SERIAL,
                "moneda": moneda,
                "total_denom": total_denom,
                "total_filas_inv": total_filas_inv,
                "ubicaciones": ubicaciones,
            },
        )

    # POST: ejecutar eliminación
    motivo_ajuste = getattr(TedMovimiento, "MOTIVO_AJUSTE", None)

    # Bloque 1: pasar a 0 y borrar TODO el inventario de esta moneda (todas las ubicaciones)
    # Usamos select_for_update para consistencia del stock.
    inv_qs = _inv_manager(for_update=True).filter(denominacion__in=den_qs)
    for inv in inv_qs:
        if motivo_ajuste is not None and inv.cantidad and inv.cantidad != 0:
            try:
                TedMovimiento.objects.create(
                    denominacion=inv.denominacion,
                    delta=-inv.cantidad,
                    motivo=motivo_ajuste,
                    creado_por=request.user,
                    transaccion_ref=f"ELIMINAR_MONEDA[{moneda.codigo}]",
                )
            except Exception:
                # En caso de que el modelo de movimientos tenga restricciones,
                # igual llevamos el inventario a cero y seguimos.
                pass
        inv.cantidad = 0
        inv.save()
        # Si el modelo tiene 'ubicacion', eliminamos la fila para no dejar residuos
        if hasattr(inv, "delete"):
            inv.delete()

    # Bloque 2: desactivar denominaciones para preservar historial (no las borramos por si están referenciadas)
    den_qs.update(activa=False)

    # Bloque 3: ocultar la moneda del terminal
    if getattr(moneda, "admite_terminal", None) is not None and moneda.admite_terminal:
        moneda.admite_terminal = False
        moneda.save(update_fields=["admite_terminal"])

    messages.success(request, f"Se eliminó la moneda {moneda.codigo} del TED (inventario y denominaciones desactivadas).")
    return redirect("admin_panel:ted:inventario")

# ──────────────────────────────────────────────────────────────────────────────
# Endpoints JSON para el kiosco
# ──────────────────────────────────────────────────────────────────────────────

@login_required  # ← solo login; sin permiso extra
def monedas_disponibles(request):
    """
    Devuelve las monedas con stock (>0) para la ubicación dada.
    Parámetro: ?ubicacion=...
    """
    ubicacion = (request.GET.get("ubicacion") or TED_DIRECCION).strip()

    qs = (
        TedInventario.objects
        .filter(
            cantidad__gt=0,
            denominacion__activa=True,
            denominacion__moneda__admite_terminal=True,
        )
        .exclude(denominacion__moneda__codigo__iexact="PYG")
    )
    qs = _inv_filter_by_ubicacion(qs, ubicacion)
    qs = (qs
        .select_related("denominacion__moneda")
        .values_list("denominacion__moneda__codigo", flat=True)
        .distinct()
        .order_by("denominacion__moneda__codigo")
    )
    return JsonResponse({"monedas": list(qs)})


@login_required  # ← solo login; sin permiso extra
def ubicaciones_disponibles(request):
    """
    Devuelve todas las ubicaciones de inventario TED en formato JSON.

    :param request: HttpRequest
    :return: JsonResponse {'ubicaciones': [str]}
    """
    return JsonResponse({"ubicaciones": _inv_distinct_ubicaciones()})