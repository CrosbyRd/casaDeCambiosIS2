from django.test import SimpleTestCase
from django.urls import reverse, resolve
from clientes import views

class ClienteUrlsTest(SimpleTestCase):
    def test_url_lista(self):
        url = reverse("clientes:lista")
        self.assertEqual(resolve(url).func.view_class, views.ClienteListView)

    def test_url_detalle(self):
        url = reverse("clientes:detalle", args=["11111111-1111-1111-1111-111111111111"])
        self.assertEqual(resolve(url).func.view_class, views.ClienteDetailView)

    def test_url_crear(self):
        url = reverse("clientes:crear")
        self.assertEqual(resolve(url).func.view_class, views.ClienteCreateView)
