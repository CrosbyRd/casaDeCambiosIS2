from django.test import TestCase
from cotizaciones.forms import CotizacionForm
from monedas.models import Moneda

class CotizacionFormTest(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar")

    def test_form_valido(self):
        form = CotizacionForm(data={
            "moneda_destino": self.moneda.id,
            "valor_compra": "7200.0000",
            "valor_venta": "7300.0000",
            "comision_compra": "5.0000",
            "comision_venta": "10.0000",
        })
        self.assertTrue(form.is_valid())

    def test_form_invalido(self):
        form = CotizacionForm(data={})
        self.assertFalse(form.is_valid())
