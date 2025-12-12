# ganancias/tests/tests_urls.py
from django.test import TestCase
from django.urls import reverse, resolve
from ganancias import views


class GananciasUrlsTest(TestCase):

    def test_dashboard_url_name(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertEqual(url, "/ganancias/dashboard/")

    def test_dashboard_url_with_app_name(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertTrue(url.startswith("/ganancias/dashboard"))

    def test_dashboard_url_pattern(self):
        resolver = resolve("/ganancias/dashboard/")
        self.assertEqual(resolver.view_name, "ganancias:dashboard_ganancias")

    def test_dashboard_url_resolves_to_function(self):
        resolver = resolve("/ganancias/dashboard/")
        self.assertEqual(resolver.func.__name__, views.dashboard_ganancias.__name__)

    def test_dashboard_url_reverse_string(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertEqual(str(url), "/ganancias/dashboard/")

    def test_dashboard_url_resolve_kwargs_empty(self):
        resolver = resolve("/ganancias/dashboard/")
        self.assertEqual(resolver.kwargs, {})

