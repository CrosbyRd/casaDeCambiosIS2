# ted/views.py
"""
Vistas del módulo TED (Terminal).
=================================
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
    monedas = _monedas_operables()
    return render(request, "ted/panel.html", {"monedas": monedas})


@login_required
@permission_required("ted.puede_operar_terminal", raise_exception=True)
@transaction.atomic
def operar(request):
    """
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
    ticket = request.session.get("ted_ticket")
    if not ticket:
        messages.error(request, "Ticket no disponible o expirado.")
        return redirect("admin_panel:ted:panel")
    return render(request, "ted/ticket_popup.html", {"t": ticket})


@login_required
@permission_required("ted.puede_operar_terminal", raise_exception=True)
def cheque_mock(request):
    monedas = _monedas_operables()
    return render(request, "ted/cheque_mock.html", {"monedas": monedas})


# =============================
# Sección INVENTARIO (ADMIN)
# =============================

@login_required
def inventario(request):
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
def eliminar_denominacion(request, den_id: int):
    resp = _check_inv_perm(request)
    if resp:
        return resp

    ubicacion = request.GET.get("ubicacion") or request.POST.get("ubicacion") or TED_DIRECCION
    den = get_object_or_404(TedDenominacion.objects.select_related("moneda"), pk=den_id)
    inv = _inv_get(den, ubicacion, for_update=True)

    if request.method == "GET":
        return render(
            request,
            "ted/admin_eliminar_den.html",
            {"den": den, "inv": inv, "serial": TED_SERIAL, "ubicacion": ubicacion},
        )

    if inv:
        if inv.cantidad != 0:
            motivo_ajuste = getattr(TedMovimiento, "MOTIVO_AJUSTE", None)
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
        if hasattr(inv, "ubicacion"):
            inv.delete()
        messages.success(request, "Denominación eliminada para esta ubicación.")
    else:
        messages.info(request, "La denominación no tiene inventario en esta ubicación.")

    if request.GET.get("ubicacion") or request.POST.get("ubicacion"):
        return redirect(f"{request.build_absolute_uri('/admin_panel/ted/inventario/')}?ubicacion={ubicacion}")
    return redirect("/admin_panel/ted/inventario/")


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
    Devuelve el listado de ubicaciones distintas presentes en TedInventario.
    """
    return JsonResponse({"ubicaciones": _inv_distinct_ubicaciones()})