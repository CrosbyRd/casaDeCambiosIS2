# ganancias/tests/tests_urls.py
from django.test import TestCase
from django.urls import reverse, resolve
from ganancias import views


class GananciasUrlsTest(TestCase):

    def test_dashboard_url_resolves_correct_view(self):
        url = reverse("ganancias:dashboard_ganancias")
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.dashboard_ganancias)

    def test_dashboard_url_name(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertEqual(url, "/dashboard/")

    def test_dashboard_url_with_app_name(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertTrue(url.startswith("/dashboard"))

    def test_dashboard_url_reverse_and_resolve_match(self):
        url = reverse("ganancias:dashboard_ganancias")
        resolver = resolve(url)
        self.assertEqual(resolver.view_name, "ganancias:dashboard_ganancias")

    def test_dashboard_url_is_accessible(self):
        response = self.client.get(reverse("ganancias:dashboard_ganancias"))
        # No autenticado → redirige al login
        self.assertEqual(response.status_code, 302)

    def test_dashboard_url_pattern(self):
        resolver = resolve("/dashboard/")
        self.assertEqual(resolver.view_name, "ganancias:dashboard_ganancias")

    def test_dashboard_url_in_namespace(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertIn("ganancias", url or "ganancias:dashboard_ganancias")

    def test_dashboard_url_resolves_to_function(self):
        resolver = resolve("/dashboard/")
        self.assertEqual(resolver.func.__name__, views.dashboard_ganancias.__name__)

    def test_dashboard_url_reverse_string(self):
        url = reverse("ganancias:dashboard_ganancias")
        self.assertEqual(str(url), "/dashboard/")

    def test_dashboard_url_resolve_kwargs_empty(self):
        resolver = resolve("/dashboard/")
        self.assertEqual(resolver.kwargs, {})
