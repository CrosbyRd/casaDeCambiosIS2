# ted/views.py — REEMPLAZO COMPLETO
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from monedas.models import Moneda, TedDenominacion, TedInventario, TedMovimiento
from .services import get_cotizacion_vigente
from .forms import AjusteInventarioForm

# ──────────────────────────────────────────────────────────────────────────────
# Config del equipo (mock)
TED_SERIAL = "TED-AGSL-0001"
TED_DIRECCION = "Campus, San Lorenzo – Paraguay"
# ──────────────────────────────────────────────────────────────────────────────

# Permisos compatibles para Inventario TED (acepta cualquiera de estos)
PERM_INV_MAIN = "monedas.puede_gestionar_inventario"
PERM_INV_ALT1 = "monedas.access_ted_inventory"
PERM_INV_ALT2 = "ted.puede_gestionar_inventario"


def _check_inv_perm(request):
    u = request.user
    if not (u.has_perm(PERM_INV_MAIN) or u.has_perm(PERM_INV_ALT1) or u.has_perm(PERM_INV_ALT2)):
        raise PermissionDenied


def _is_pyg(moneda: Moneda) -> bool:
    return moneda.codigo.upper() == "PYG"


def _monedas_operables():
    base = Moneda.objects.exclude(codigo__iexact="PYG").order_by("codigo")
    marcadas = base.filter(admite_terminal=True)
    return marcadas if marcadas.exists() else base


# =========================
# Sección OPERATIVA (igual)
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
                inv, _ = TedInventario.objects.select_for_update().get_or_create(
                    denominacion=den, defaults={"cantidad": 0}
                )
                if inv.cantidad < q:
                    messages.error(
                        request,
                        f"Stock insuficiente para {den.valor} {moneda.codigo}. Disponible: {inv.cantidad}."
                    )
                    return redirect(f"{request.path}?moneda={moneda.id}")

        # Aplica movimientos e inventario
        for den, q in cantidades:
            inv, _ = TedInventario.objects.select_for_update().get_or_create(
                denominacion=den, defaults={"cantidad": 0}
            )
            inv.cantidad = inv.cantidad + signo * q
            inv.save()

            TedMovimiento.objects.create(
                denominacion=den,
                delta=signo * q,
                motivo=motivo,
                creado_por=request.user,
                transaccion_ref="",  # mock por ahora
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
    _check_inv_perm(request)
    """
    Vista principal de inventario TED.
    """
    den_qs = (
        TedDenominacion.objects
        .filter(activa=True, moneda__admite_terminal=True)
        .select_related("moneda")
        .order_by("moneda__codigo", "valor")
    )

    inv_map = {
        i.denominacion_id: i
        for i in TedInventario.objects.filter(denominacion__in=den_qs)
    }

    grupos = []
    actual = None
    for den in den_qs:
        if not actual or actual["moneda"].id != den.moneda_id:
            actual = {"moneda": den.moneda, "items": []}
            grupos.append(actual)
        stock = inv_map.get(den.id)
        actual["items"].append({
            "den": den,
            "stock": stock.cantidad if stock else 0,
        })

    ctx = {
        "serial": TED_SERIAL,
        "direccion": TED_DIRECCION,
        "grupos": grupos,
    }
    return render(request, "ted/admin_inventario.html", ctx)


@login_required
@transaction.atomic
def inventario_ajustar(request, den_id: int):
    _check_inv_perm(request)

    den = get_object_or_404(
        TedDenominacion.objects.select_related("moneda"),
        pk=den_id, activa=True
    )
    inv, _ = TedInventario.objects.select_for_update().get_or_create(
        denominacion=den, defaults={"cantidad": 0}
    )

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
                    transaccion_ref=comentario[:64],  # breve nota
                )
                messages.success(request, "Ajuste aplicado correctamente.")
                return redirect("admin_panel:ted:inventario")
    else:
        form = AjusteInventarioForm(initial={"delta": 0})

    return render(
        request,
        "ted/admin_ajustar.html",
        {"den": den, "inv": inv, "serial": TED_SERIAL, "direccion": TED_DIRECCION, "form": form},
    )


@login_required
def inventario_movimientos(request):
    _check_inv_perm(request)

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
# NUEVO: crear stock (denominaciones + inventario inicial)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@transaction.atomic
def crear_stock(request):
    _check_inv_perm(request)

    # Monedas candidatas (todas menos PYG)
    monedas = Moneda.objects.exclude(codigo__iexact="PYG").order_by("codigo")

    if request.method == "POST":
        moneda_id = request.POST.get("moneda")
        if not moneda_id:
            messages.error(request, "Seleccione una moneda.")
            return render(request, "ted/admin_crear_stock.html", {
                "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION
            })

        moneda = get_object_or_404(Moneda, pk=moneda_id)

        # Lee arrays del formulario
        vals = request.POST.getlist("den_valor[]")
        stocks = request.POST.getlist("den_stock[]")

        filas = []
        for v, s in zip(vals, stocks):
            if (v or "").strip() == "" and (s or "").strip() == "":
                continue
            try:
                valor = Decimal(v)
                if valor <= 0:
                    raise InvalidOperation
            except Exception:
                messages.error(request, f"Valor de denominación inválido: {v!r}")
                return render(request, "ted/admin_crear_stock.html", {
                    "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION
                })
            try:
                cantidad = int(s)
                if cantidad < 0:
                    raise ValueError
            except Exception:
                messages.error(request, f"Stock inválido para la denominación {v}.")
                return render(request, "ted/admin_crear_stock.html", {
                    "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION
                })
            filas.append((valor, cantidad))

        if not filas:
            messages.error(request, "Agregue al menos una fila de denominación/stock.")
            return render(request, "ted/admin_crear_stock.html", {
                "monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION
            })

        # Crea/actualiza denominaciones e inventario
        for valor, cantidad in filas:
            den, _ = TedDenominacion.objects.get_or_create(
                moneda=moneda,
                valor=valor,
                defaults={"activa": True},
            )
            if not den.activa:
                den.activa = True
                den.save(update_fields=["activa"])

            inv, created = TedInventario.objects.select_for_update().get_or_create(
                denominacion=den, defaults={"cantidad": 0}
            )
            prev = inv.cantidad
            inv.cantidad = cantidad  # set explícito al valor ingresado
            inv.save()

            # Registrar movimiento si hay delta y el modelo lo permite
            delta = inv.cantidad - prev
            motivo_ajuste = getattr(TedMovimiento, "MOTIVO_AJUSTE", None)
            if delta != 0 and motivo_ajuste is not None:
                TedMovimiento.objects.create(
                    denominacion=den,
                    delta=delta,
                    motivo=motivo_ajuste,
                    creado_por=request.user,
                    transaccion_ref="CREAR_STOCK",
                )

        # Habilita moneda en la terminal
        if not moneda.admite_terminal:
            moneda.admite_terminal = True
            moneda.save(update_fields=["admite_terminal"])

        messages.success(request, "Stock creado/actualizado correctamente.")
        return redirect("admin_panel:ted:inventario")

    # GET
    return render(
        request,
        "ted/admin_crear_stock.html",
        {"monedas": monedas, "serial": TED_SERIAL, "direccion": TED_DIRECCION},
    )


# ──────────────────────────────────────────────────────────────────────────────
# NUEVO: eliminar denominación (soft-delete: desactivar + limpiar inventario)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@transaction.atomic
def eliminar_denominacion(request, den_id: int):
    _check_inv_perm(request)

    den = get_object_or_404(
        TedDenominacion.objects.select_related("moneda"),
        pk=den_id
    )
    # Desactivar y poner inventario en 0
    inv = TedInventario.objects.select_for_update().filter(denominacion=den).first()
    if inv and inv.cantidad != 0:
        # Registrar salida si existe motivo ajuste
        motivo_ajuste = getattr(TedMovimiento, "MOTIVO_AJUSTE", None)
        delta = -inv.cantidad
        inv.cantidad = 0
        inv.save()
        if motivo_ajuste is not None and delta != 0:
            TedMovimiento.objects.create(
                denominacion=den,
                delta=delta,
                motivo=motivo_ajuste,
                creado_por=request.user,
                transaccion_ref="ELIMINAR_DENOMINACION",
            )

    den.activa = False
    den.save(update_fields=["activa"])
    messages.success(request, "Denominación desactivada y stock limpiado.")
    return redirect("admin_panel:ted:inventario")