# CasaDeCambioIS2/views.py
from django.shortcuts import render
from cotizaciones.models import Cotizacion

# Bandera por código (usada en Home)
EMOJI_BY_CODE = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "BRL": "🇧🇷", "PYG": "🇵🇾",
    "ARS": "🇦🇷", "CLP": "🇨🇱", "COP": "🇨🇴", "MXN": "🇲🇽",
    "PEN": "🇵🇪", "UYU": "🇺🇾", "GBP": "🇬🇧", "JPY": "🇯🇵",
    "CNY": "🇨🇳", "AUD": "🇦🇺", "CAD": "🇨🇦", "CHF": "🇨🇭",
}

DESTINO_PUBLICO = "PYG"  # En sitio público siempre mostramos “XXX → PYG”

def _rows_from_qs(qs):
    """
    Normaliza filas para las plantillas públicas.
    En tu BD: moneda_base siempre es PYG y moneda_destino es la divisa (USD/EUR/…).
    En la UI pública queremos mostrar “DIVISA → PYG”, con los valores tal como los guardás.
    """
    rows = []
    for c in qs:
        divisa = c.moneda_destino  # USD/EUR/…
        rows.append({
            "codigo": divisa.codigo,
            "nombre": divisa.nombre,
            "emoji": EMOJI_BY_CODE.get(divisa.codigo, "💱"),
            "valor_compra": c.valor_compra,
            "valor_venta": c.valor_venta,
            "fecha_actualizacion": c.fecha_actualizacion,
        })
    return rows

def site_rates(request):
    # Traer todas las cotizaciones donde la base sea PYG (como se guarda en tu ABM)
    qs = (
        Cotizacion.objects
        .select_related("moneda_base", "moneda_destino")
        .filter(moneda_base__codigo="PYG")
        .order_by("moneda_destino__codigo")
    )
    return render(request, "site/rates.html", {
        "cotizaciones": _rows_from_qs(qs),
        "destino_publico": DESTINO_PUBLICO,
    })

def site_home(request):
    # Todas hacia PYG (base PYG en BD)
    all_qs = list(
        Cotizacion.objects
        .select_related("moneda_base", "moneda_destino")
        .filter(moneda_base__codigo="PYG")
    )

    preferidas = ["USD", "EUR", "BRL"]
    por_codigo = {c.moneda_destino.codigo: c for c in all_qs}

    destacadas = []
    for code in preferidas:
        if code in por_codigo:
            destacadas += _rows_from_qs([por_codigo[code]])

    if len(destacadas) < 3:
        usados = {r["codigo"] for r in destacadas}
        for c in all_qs:
            code = c.moneda_destino.codigo
            if code not in usados:
                destacadas += _rows_from_qs([c])
                usados.add(code)
            if len(destacadas) == 3:
                break

    ultima_actualizacion = max(
        (r["fecha_actualizacion"] for r in destacadas),
        default=None
    )

    return render(request, "site/home.html", {
        "destacadas": destacadas,
        "ultima_actualizacion": ultima_actualizacion,
        "destino_publico": DESTINO_PUBLICO,
    })
