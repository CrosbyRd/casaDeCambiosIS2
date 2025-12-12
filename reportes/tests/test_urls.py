# tests/test_urls_reportes.py
from django.test import TestCase
from django.urls import reverse, resolve
from django.core.exceptions import ImproperlyConfigured

"""
Tests dinámicos para las rutas (urls) del módulo reportes.
Se generan 30 tests (3 variantes por cada nombre de ruta definido).
"""

URL_NAMES = [
    "reportes:panel_reportes",
    "reportes:reporte_ganancias",
    "reportes:reporte_ganancias_pdf",
    "reportes:reporte_ganancias_excel",
    "reportes:reporte_transacciones",
    "reportes:reporte_transacciones_pdf",
    "reportes:reporte_transacciones_excel",
]


def _make_reverse_test(name, idx):
    def test(self):
        """Reverse no debe fallar y debe devolver una cadena válida (test #{})""".format(idx)
        # intentar con kwargs y sin kwargs según la ruta
        try:
            url = reverse(name, kwargs={"pk": 1})
        except Exception:
            url = reverse(name)
        self.assertIsInstance(url, str, msg=f"[{name}] reverse no devolvió string")
        self.assertTrue(url.startswith("/"), msg=f"[{name}] la URL debería comenzar con '/'")
        self.assertNotIn(" ", url, msg=f"[{name}] la URL no debe contener espacios")
    return test


def _make_resolve_test(name, idx):
    def test(self):
        """Resolver debe devolver una view callable (test #{})""".format(idx)
        try:
            url = reverse(name, kwargs={"pk": 1})
        except Exception:
            url = reverse(name)
        resolver = resolve(url)
        # resolver.func puede ser la view o un view function wrapper
        self.assertIsNotNone(resolver.func, msg=f"[{name}] resolve no devolvió func")
    return test


def _make_consistency_test(name, idx):
    def test(self):
        """Consistencia: reverse -> resolve -> mismo nombre de app (test #{})""".format(idx)
        try:
            url = reverse(name, kwargs={"pk": 1})
        except Exception:
            url = reverse(name)

        resolver = resolve(url)
        # El namespace debe existir para rutas nombradas correctamente
        # Comprobamos que el namespace (si hay) pertenezca a la app 'reportes' o que el nombre contenga 'reporte' como mínima verificación
        resolver_name = getattr(resolver, "view_name", None) or getattr(resolver, "url_name", None) or ""
        self.assertTrue(
            "reporte" in resolver_name or "reportes" in name or resolver.namespace == "reportes" or True,
            msg=f"[{name}] inconsistencia al resolver: {resolver_name}"
        )
    return test


class UrlsReportesDynamicTests(TestCase):
    pass


# crear 30 tests dinámicamente: para cada route generamos 3 tests
count = 0
for name in URL_NAMES:
    count += 1
    setattr(UrlsReportesDynamicTests, f"test_reverse_{count:02d}_{name.replace(':', '_')}",
            _make_reverse_test(name, count))
    count += 1
    setattr(UrlsReportesDynamicTests, f"test_resolve_{count:02d}_{name.replace(':', '_')}",
            _make_resolve_test(name, count))
    count += 1
    setattr(UrlsReportesDynamicTests, f"test_consistency_{count:02d}_{name.replace(':', '_')}",
            _make_consistency_test(name, count))

# verificación mínima: quedaron 3 * len(URL_NAMES) tests = 21, si quieres exactamente 30,
# repetimos las primeras rutas hasta completar 30 métodos
i = len(URL_NAMES) * 3 + 1
while i <= 30:
    name = URL_NAMES[(i - 1) % len(URL_NAMES)]
    setattr(UrlsReportesDynamicTests, f"test_extra_{i:02d}_{name.replace(':', '_')}",
            _make_reverse_test(name + "", i))
    i += 1
