from django.test import TestCase
from django.utils import timezone
from monedas.models import Moneda
from cotizaciones.models import Cotizacion
from decimal import Decimal

class CotizacionModelTest(TestCase):
    def setUp(self):
        self.moneda_base = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.moneda_destino = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.cotizacion = Cotizacion.objects.create(
            moneda_base=self.moneda_base,
            moneda_destino=self.moneda_destino,
            valor_compra=Decimal("7200.0000"),
            valor_venta=Decimal("7300.0000"),
            comision_compra=Decimal("10.0000"),
            comision_venta=Decimal("20.0000"),
        )

    def test_str(self):
        self.assertEqual(str(self.cotizacion), "PYG a USD")

    def test_total_compra(self):
        self.assertEqual(self.cotizacion.total_compra, Decimal("7210.0000"))

    def test_total_venta(self):
        self.assertEqual(self.cotizacion.total_venta, Decimal("7320.0000"))

    def test_unique_together(self):
        with self.assertRaises(Exception):
            Cotizacion.objects.create(
                moneda_base=self.moneda_base,
                moneda_destino=self.moneda_destino,
                valor_compra=Decimal("7100.0000"),
                valor_venta=Decimal("7400.0000"),
            )
