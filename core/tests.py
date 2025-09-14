# core/tests.py
from django.test import TestCase
from decimal import Decimal
from .logic import calcular_simulacion

class SimulacionLogicTest(TestCase):
    
    def test_venta_usd_minorista(self):
        """Prueba la venta de USD (PYG -> USD) para un cliente minorista."""
        resultado = calcular_simulacion(
            monto_origen=Decimal('755000'),
            moneda_origen='PYG',
            moneda_destino='USD',
            tipo_cliente='MINORISTA'
        )
        # Tasa Venta USD = 7450 (base) + 100 (comision) - 0 (bonif) = 7550
        # 755000 / 7550 = 100
        self.assertIsNone(resultado['error'])
        self.assertEqual(resultado['monto_recibido'], Decimal('100.00'))
        self.assertEqual(resultado['tasa_aplicada'], Decimal('7550.00'))

    def test_compra_eur_vip(self):
        """Prueba la compra de EUR (EUR -> PYG) para un cliente VIP (10% bonif)."""
        resultado = calcular_simulacion(
            monto_origen=Decimal('100'),
            moneda_origen='EUR',
            moneda_destino='PYG',
            tipo_cliente='VIP'
        )
        # Comision EUR = 60. Descuento VIP (10%) = 6. Comision final = 54.
        # Tasa Compra EUR = 8100 (base) - 54 (comision final) = 8046
        # 100 * 8046 = 804600
        self.assertIsNone(resultado['error'])
        self.assertEqual(resultado['monto_recibido'], Decimal('804600.00'))
        self.assertEqual(resultado['bonificacion_aplicada'], Decimal('6.00')) # 10% de 60
        self.assertEqual(resultado['tasa_aplicada'], Decimal('8046.00'))

    def test_error_moneda_invalida(self):
        """Prueba que la función devuelve un error si la moneda no existe."""
        resultado = calcular_simulacion(
            monto_origen=Decimal('1000'),
            moneda_origen='PYG',
            moneda_destino='BTC', # Moneda no simulada
            tipo_cliente='MINORISTA'
        )
        self.assertIsNotNone(resultado['error'])
        self.assertIn('BTC', resultado['error'])

    def test_error_transaccion_no_pyg(self):
        """Prueba que la función devuelve un error si no se involucra PYG."""
        resultado = calcular_simulacion(
            monto_origen=Decimal('100'),
            moneda_origen='USD',
            moneda_destino='EUR',
            tipo_cliente='MINORISTA'
        )
        self.assertIsNotNone(resultado['error'])
        self.assertIn('debe ser entre PYG', resultado['error'])
        
# Para ejecutar las pruebas: python manage.py test core