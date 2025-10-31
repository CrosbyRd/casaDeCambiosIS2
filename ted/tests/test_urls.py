from django.test import SimpleTestCase
from django.urls import reverse, resolve
from ted import views

class TedUrlsTests(SimpleTestCase):
    def test_url_panel_resolve(self):
        url = reverse('ted:panel')
        self.assertEqual(resolve(url).func, views.panel)

    def test_url_operar_resolve(self):
        self.assertEqual(resolve(reverse('ted:operar')).func, views.operar)

    def test_url_inventario_resolve(self):
        self.assertEqual(resolve(reverse('ted:inventario')).func, views.inventario)

    def test_url_ajustar_dinamica(self):
        url = reverse('ted:inventario_ajustar', args=[1])
        self.assertIn('/inventario/ajustar/', url)
