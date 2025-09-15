from django.test import TestCase
from monedas.models import Moneda

class MonedaModelTests(TestCase):

    def test_creacion_moneda(self):
        moneda = Moneda.objects.create(
            codigo="USD",
            nombre="Dólar estadounidense",
            simbolo="$",
            decimales=2,
            minima_denominacion=1,
            admite_en_linea=True,
            admite_terminal=True
        )
        self.assertEqual(moneda.codigo, "USD")
        self.assertEqual(moneda.nombre, "Dólar estadounidense")
        self.assertEqual(moneda.simbolo, "$")
        self.assertEqual(moneda.decimales, 2)
        self.assertEqual(moneda.minima_denominacion, 1)
        self.assertTrue(moneda.admite_en_linea)
        self.assertTrue(moneda.admite_terminal)

    def test_str_moneda(self):
        moneda = Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="₲")
        self.assertEqual(str(moneda), "Guaraní (PYG)")
