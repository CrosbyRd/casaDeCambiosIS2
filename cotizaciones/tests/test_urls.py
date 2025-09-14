from django.test import SimpleTestCase
from django.urls import reverse, resolve
from cotizaciones import views

class CotizacionUrlsTest(SimpleTestCase):
    def test_cotizacion_list_url(self):
        url = reverse("cotizaciones:cotizacion_list")
        self.assertEqual(resolve(url).func, views.cotizacion_list)

    def test_cotizacion_create_url(self):
        url = reverse("cotizaciones:cotizacion_create")
        self.assertEqual(resolve(url).func, views.cotizacion_create)
