# CasaDeCambioIS2/context_processors.py
from __future__ import annotations

import json
from typing import Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from django.core.cache import cache

# Importamos aquí para evitar dependencias cíclicas en settings
try:
    from monedas.models import Moneda
except Exception:
    Moneda = None  # en migraciones o entornos sin app lista


API_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/pyg.json"
API_FALLBACK = "https://latest.currency-api.pages.dev/v1/currencies/pyg.json"

CACHE_KEY = "fx_pyg_json"
CACHE_TTL = 60 * 60  # 1 hora


def _fetch_json(url: str) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=8) as resp:
        if resp.status != 200:
            raise HTTPError(url, resp.status, "Bad status", resp.headers, None)
        return json.loads(resp.read().decode("utf-8"))


def _get_latest_rates() -> Dict[str, Any]:
    """
    Descarga el JSON (base: PYG) con fallback y lo cachea.
    Formato esperado:
    {
      "date": "2025-08-26",
      "pyg": {
        "usd": 0.00013,
        "eur": 0.00011,
        ...
      }
    }
    """
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    data = None
    try:
        data = _fetch_json(API_PRIMARY)
    except Exception:
        try:
            data = _fetch_json(API_FALLBACK)
        except Exception:
            data = None

    if not isinstance(data, dict) or "pyg" not in data:
        # Guardamos un marcador vacío breve para evitar golpear la API en bucle
        cache.set(CACHE_KEY, {"date": None, "pyg": {}}, 300)
        return {"date": None, "pyg": {}}

    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data


def currency_context(request):
    """
    Expone en templates:
      - fx.date -> fecha string o None
      - fx.by_code -> dict { "USD": { "pyg_per_unit": 7300.12 }, ... }
      - fx.available -> set de códigos en el JSON
      - monedas -> queryset de Moneda (si app disponible)
    """
    data = _get_latest_rates()
    rates = data.get("pyg") or {}
    date = data.get("date")

    by_code: Dict[str, Dict[str, Any]] = {}

    # Si no hay modelo (por migraciones) devolvemos estructura vacía
    monedas_qs = Moneda.objects.all() if Moneda else []

    for m in monedas_qs:
        code = (m.codigo or "").upper()
        if code == "PYG":
            # 1 PYG = 1 PYG
            by_code["PYG"] = {"pyg_per_unit": 1.0}
            continue

        # La API devuelve claves en minúsculas
        api_key = code.lower()
        usd_per_pyg = rates.get(api_key)  # OJO: es TARGET per 1 PYG
        # Queremos PYG por 1 TARGET -> 1 / (TARGET per PYG)
        if isinstance(usd_per_pyg, (int, float)) and usd_per_pyg > 0:
            pyg_per_unit = 1.0 / float(usd_per_pyg)
            by_code[code] = {"pyg_per_unit": pyg_per_unit}
        else:
            # Si el par no existe en la API, lo omitimos (o podrías poner None)
            by_code[code] = {"pyg_per_unit": None}

    ctx = {
        "fx": {
            "date": date,
            "by_code": by_code,
            "available": {k.upper() for k in rates.keys()},
        },
        "monedas": monedas_qs,
    }
    return ctx

