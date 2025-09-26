from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from monedas.models import Moneda, TedDenominacion, TedInventario, TedMovimiento
from .services import get_cotizacion_vigente


def _is_pyg(moneda: Moneda) -> bool:
    return moneda.codigo.upper() == "PYG"


def _monedas_operables():
    """
    Devuelve monedas para el selector de TED:
    - Si hay monedas con admite_terminal=True, usa esas (excluye PYG).
    - Si no hay ninguna marcada aún, hace fallback a todas las extranjeras (excluye PYG).
    """
    base = Moneda.objects.exclude(codigo__iexact="PYG").order_by("codigo")
    marcadas = base.filter(admite_terminal=True)
    return marcadas if marcadas.exists() else base


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
    # Por defecto mostramos COMPRA en GET si no viene explícito
    operacion = (request.POST.get("operacion") or request.GET.get("operacion") or "COMPRA").upper()
    if operacion not in ("COMPRA", "VENTA"):
        operacion = "COMPRA"

    # Si entran sin seleccionar moneda, volvemos al panel
    if request.method == "GET" and not moneda_id:
        messages.error(request, "Selecciona una moneda para operar.")
        return redirect("admin_panel:ted:panel")

    moneda = None
    denominaciones = []
    cotiz = None
    tasa_display = None

    if moneda_id:
        try:
            moneda = Moneda.objects.get(id=moneda_id)
            if _is_pyg(moneda):
                messages.error(request, "Solo se permiten operaciones PYG ↔ Moneda extranjera.")
                return redirect("admin_panel:ted:panel")

            denominaciones = (
                TedDenominacion.objects.filter(moneda=moneda, activa=True).order_by("valor")
            )
            cotiz = get_cotizacion_vigente(moneda)
            if cotiz:
                # Para la tarjeta de “Tasa aplicada” del template
                tasa_display = cotiz["venta"] if operacion == "COMPRA" else cotiz["compra"]
        except Moneda.DoesNotExist:
            moneda = None

    if request.method == "POST":
        if not moneda:
            messages.error(request, "Seleccione una moneda.")
            return redirect("admin_panel:ted:operar")

        allow_stale = getattr(settings, "TED_ALLOW_STALE_RATES", False)
        if not cotiz or (not cotiz.get("vigente") and not allow_stale):
            messages.error(request, "No hay una cotización vigente (≤ ventana configurada). Actualiza las tasas.")
            return redirect(f"{request.path}?moneda={moneda.id}&operacion={operacion}")

        # Parseo de cantidades por denominación (input name: denom_<id>)
        cantidades = []
        total_ext = Decimal("0")
        for den in denominaciones:
            key = f"denom_{den.id}"
            try:
                q = int(request.POST.get(key, "0") or "0")
                if q < 0:
                    raise ValueError
            except ValueError:
                messages.error(request, "Cantidades inválidas.")
                return redirect(f"{request.path}?moneda={moneda.id}&operacion={operacion}")

            if q > 0:
                cantidades.append((den, q))
                total_ext += Decimal(den.valor) * q

        if total_ext <= 0:
            messages.error(request, "Ingrese al menos una denominación.")
            return redirect(f"{request.path}?moneda={moneda.id}&operacion={operacion}")

        # Determina tasa y signo de inventario
        if operacion == "COMPRA":
            tasa = cotiz["venta"]   # vendemos extranjera → cobramos en PYG
            motivo = TedMovimiento.MOTIVO_COMPRA
            signo = -1              # retiramos billetes (descarga stock)
        else:
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
                    return redirect(f"{request.path}?moneda={moneda.id}&operacion={operacion}")

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

        # Guarda datos de ticket en sesión (mock transacción)
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

    operacion_label = (
        "Compra (retiro billetes)" if operacion == "COMPRA" else "Venta (depósito billetes)"
    )

    ctx = {
        "monedas": monedas,
        "moneda": moneda,
        "denominaciones": denominaciones,
        "cotiz": cotiz,
        "tasa": tasa_display,
        "operacion": operacion,
        "operacion_label": operacion_label,
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
    """Mock de depósito de cheques: solo HTML."""
    monedas = _monedas_operables()
    return render(request, "ted/cheque_mock.html", {"monedas": monedas})
