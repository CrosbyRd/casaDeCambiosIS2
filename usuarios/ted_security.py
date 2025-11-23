"""
Seguridad para endpoints TED
============================

.. module:: usuarios.ted_security
   :synopsis: Decorador para exigir API-Key de terminal (opcional).

Si ``settings.TED_REQUIRE_KEY`` es ``True``, exige cabecera ``X-TED-KEY``.
En desarrollo (o si la flag es False), permite el acceso sin bloquear.

Integración:
------------
from usuarios.ted_security import require_ted_key

@require_ted_key
def mi_view(request): ...
"""
from django.conf import settings
from django.http import JsonResponse

def require_ted_key(view):
    def _wrapped(request, *args, **kwargs):
        require = getattr(settings, "TED_REQUIRE_KEY", False)
        if not require:
            return view(request, *args, **kwargs)
        provided = request.headers.get("X-TED-KEY") or request.META.get("HTTP_X_TED_KEY")
        expected = getattr(settings, "TED_API_KEY", None)
        if expected and provided == expected:
            return view(request, *args, **kwargs)
        return JsonResponse({"ok": False, "error": "No autorizado (TED KEY)."}, status=401)
    return _wrapped
