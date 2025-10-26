"""
Catálogo TED
============

.. module:: usuarios.ted_catalog
   :synopsis: Endpoints livianos de catálogo para el kiosco TED.

- GET /usuarios/ted/api/ubicaciones/ → lista de ubicaciones (desde TedInventario o fallback)
- GET /usuarios/ted/api/terminal/    → info básica del terminal (Nº de serie)

No usa superusuario ni permisos especiales.
"""
from __future__ import annotations

from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_GET
from django.conf import settings

from monedas.models import TedInventario


@require_GET
def ubicaciones(request: HttpRequest) -> JsonResponse:
    """Devuelve ubicaciones disponibles para operar en el TED."""
    qs = (
        TedInventario.objects
        .values_list("ubicacion", flat=True)
        .exclude(ubicacion__isnull=True)
        .exclude(ubicacion__exact="")
        .distinct()
        .order_by("ubicacion")
    )
    ubicaciones = list(qs)
    if not ubicaciones:
        ubicaciones = list(getattr(settings, "TED_UBICACIONES_FALLBACK", []))
    return JsonResponse({"ok": True, "data": {"ubicaciones": ubicaciones}}, status=200)


@require_GET
def terminal_info(request: HttpRequest) -> JsonResponse:
    """
    Devuelve datos básicos del terminal (para UI del TED).

    settings:
      - TED_SERIAL (str): Nº de serie del terminal. Si no está, devuelve "LOCAL-DEV".
    """
    serial = getattr(settings, "TED_SERIAL", "") or "LOCAL-DEV"
    return JsonResponse({"ok": True, "data": {"serial": serial}}, status=200)
