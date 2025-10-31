from django.test import TestCase
from decimal import Decimal
from ted.logic import ajustar_monto_a_denominaciones_disponibles
from monedas.models import TedInventario, Moneda, TedDenominacion

class AjusteMontoTests(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(codigo='USD', nombre='Dólar')
        self.den1 = TedDenominacion.objects.create(moneda=self.moneda, valor=Decimal('10'))
        self.den2 = TedDenominacion.objects.create(moneda=self.moneda, valor=Decimal('5'))
        TedInventario.objects.create(denominacion=self.den1, cantidad=10)
        TedInventario.objects.create(denominacion=self.den2, cantidad=20)

    def test_compra_no_ajusta_monto(self):
        result = ajustar_monto_a_denominaciones_disponibles(Decimal('120'), self.moneda, 'compra')
        self.assertEqual(result['monto_ajustado'], Decimal('120'))
        self.assertFalse(result['ajustado'])

    def test_venta_ajusta_monto(self):
        result = ajustar_monto_a_denominaciones_disponibles(Decimal('180'), self.moneda, 'venta')
        self.assertTrue(result['monto_ajustado'] <= result['monto_maximo_posible'])

    def test_sin_inventario(self):
        TedInventario.objects.all().delete()
        result = ajustar_monto_a_denominaciones_disponibles(Decimal('100'), self.moneda, 'venta')
        self.assertEqual(result['monto_ajustado'], Decimal('0'))

    def test_monto_ajustado_inferior_si_insuficiente(self):
        TedInventario.objects.filter(denominacion=self.den1).update(cantidad=1)
        result = ajustar_monto_a_denominaciones_disponibles(Decimal('200'), self.moneda, 'venta')
        self.assertLess(result['monto_ajustado'], Decimal('200'))
