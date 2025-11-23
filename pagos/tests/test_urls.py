from django.test import SimpleTestCase
from django.urls import reverse, resolve
from pagos import views

class TipoMedioPagoURLsTests(SimpleTestCase):
    def test_listar_url_resuelve(self):
        url = reverse("pagos:listar_tipos_medio_pago")
        self.assertEqual(resolve(url).func, views.listar_tipos_medio_pago)

    def test_agregar_url_resuelve(self):
        url = reverse("pagos:agregar_tipo_medio_pago")
        self.assertEqual(resolve(url).func, views.agregar_tipo_medio_pago)

    def test_editar_url_resuelve(self):
        url = reverse("pagos:editar_tipo_medio_pago", args=[1])
        self.assertEqual(resolve(url).func, views.editar_tipo_medio_pago)

    def test_eliminar_url_resuelve(self):
        url = reverse("pagos:eliminar_tipo_medio_pago", args=[1])
        self.assertEqual(resolve(url).func, views.eliminar_tipo_medio_pago)

    def test_ver_url_resuelve(self):
        url = reverse("pagos:ver_tipo_medio_pago", args=[1])
        self.assertEqual(resolve(url).func, views.ver_tipo_medio_pago)

    def test_toggle_url_resuelve(self):
        url = reverse("pagos:toggle_activo", args=[1])
        self.assertEqual(resolve(url).func, views.toggle_activo_tipo_medio_pago)
