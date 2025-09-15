"""
Módulo de pruebas unitarias para la lógica de simulación de cambio de divisas.

Este módulo contiene pruebas para la función `calcular_simulacion` en `core.logic`,
asegurando que los cálculos de compra/venta, la aplicación de bonificaciones y
el manejo de errores funcionen como se espera.
"""
from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch, Mock
from core.logic import calcular_simulacion
from django.contrib.auth import get_user_model
from clientes.models import Cliente
from cotizaciones.models import Cotizacion
from monedas.models import Moneda
# Importar excepciones específicas si se desea mockearlas con precisión
from django.core.exceptions import ObjectDoesNotExist as DjangoObjectDoesNotExist

User = get_user_model()

class SimulacionLogicTest(TestCase):
    """
    Conjunto de pruebas para la función `calcular_simulacion` en `core.logic`.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Configura los datos de prueba iniciales para todas las pruebas de la clase.
        Asegura que los objetos Moneda esenciales existan en la base de datos de prueba.
        """
        Moneda.objects.create(codigo='PYG', nombre='Guaraní Paraguayo', decimales=0, minima_denominacion=Decimal('100'))
        Moneda.objects.create(codigo='USD', nombre='Dólar Estadounidense', decimales=2, minima_denominacion=Decimal('0.01'))
        Moneda.objects.create(codigo='EUR', nombre='Euro', decimales=2, minima_denominacion=Decimal('0.01'))
        # No creamos 'BTC' intencionalmente para probar escenarios de moneda no existente.

    @patch('clientes.models.Cliente.objects.first')
    @patch('cotizaciones.models.Cotizacion.objects.get')
    def test_venta_usd_minorista(self, mock_cotizacion_get, mock_cliente_first):
        """
        Prueba la venta de USD (PYG -> USD) para un cliente minorista sin bonificación.

        Verifica que el monto recibido, la tasa aplicada y la bonificación sean correctos
        cuando un cliente minorista vende PYG para comprar USD.
        """
        mock_client_instance = Mock(spec=Cliente)
        mock_client_instance.bonificacion = Decimal('0')
        mock_cliente_first.return_value = mock_client_instance

        # Mock del objeto Cotizacion con precisión Decimal apropiada
        mock_cotizacion_instance = Mock(spec=Cotizacion)
        mock_cotizacion_instance.moneda_base.codigo = 'PYG'
        mock_cotizacion_instance.moneda_destino.codigo = 'USD'
        mock_cotizacion_instance.valor_venta = Decimal('7450.0000') # Precisión explícita
        mock_cotizacion_instance.comision_venta = Decimal('100.0000') # Precisión explícita
        mock_cotizacion_get.return_value = mock_cotizacion_instance

        mock_user = User(pk=1)

        resultado = calcular_simulacion(
            monto_origen=Decimal('755000'),
            moneda_origen='PYG',
            moneda_destino='USD',
            user=mock_user
        )

        self.assertIsNone(resultado['error'])
        self.assertEqual(resultado['monto_recibido'], Decimal('100.00'))
        self.assertEqual(resultado['tasa_aplicada'], Decimal('7550.0000')) # Usar precisión consistente con el modelo
        self.assertEqual(resultado['bonificacion_aplicada'], Decimal('0.0000')) # Usar precisión consistente con el modelo

        mock_cotizacion_get.assert_called_once_with(
            moneda_base__codigo='PYG',
            moneda_destino__codigo='USD'
        )


    @patch('cotizaciones.models.Cotizacion.objects.get')
    def test_compra_eur_vip(self, mock_cotizacion_get):
        """
        Prueba la compra de EUR (EUR -> PYG) para un cliente VIP con 10% de bonificación.

        Verifica que el monto recibido, la bonificación aplicada y la tasa sean correctos
        cuando un cliente VIP compra PYG con EUR, aplicando la bonificación sobre la comisión.
        """
        mock_client_instance = Mock(spec=Cliente)
        mock_client_instance.bonificacion = Decimal('10.0') # Precisión explícita
        mock_client_instance.tipo_cliente = 'VIP'

        # Mock del objeto Cotizacion con precisión explícita
        mock_cotizacion_instance = Mock(spec=Cotizacion)
        mock_cotizacion_instance.moneda_base.codigo = 'PYG'
        mock_cotizacion_instance.moneda_destino.codigo = 'EUR'
        mock_cotizacion_instance.valor_compra = Decimal('8100.0000') # Precisión explícita
        mock_cotizacion_instance.comision_compra = Decimal('60.0000') # Precisión explícita
        mock_cotizacion_get.return_value = mock_cotizacion_instance

        mock_user = Mock(spec=User) # Crear un mock de usuario
        mock_user.is_authenticated = True # Asegurar que el usuario está autenticado
        mock_user.clientes = Mock() # Mockear el atributo 'clientes'
        mock_user.clientes.first.return_value = mock_client_instance # Configurar first() para devolver el cliente mockeado

        resultado = calcular_simulacion(
            monto_origen=Decimal('100'),
            moneda_origen='EUR',
            moneda_destino='PYG',
            user=mock_user # Pasar el usuario mockeado
        )

        self.assertIsNone(resultado['error'])
        self.assertEqual(resultado['monto_recibido'], Decimal('804600.00'))
        self.assertEqual(resultado['bonificacion_aplicada'], Decimal('6.0000')) # Precisión explícita
        self.assertEqual(resultado['tasa_aplicada'], Decimal('8046.0000')) # Precisión explícita

        mock_cotizacion_get.assert_called_once_with(
            moneda_base__codigo='PYG',
            moneda_destino__codigo='EUR'
        )


    @patch('monedas.models.Moneda.objects.get') # Mockear sin side_effect inicialmente
    @patch('cotizaciones.models.Cotizacion.objects.get', side_effect=Cotizacion.DoesNotExist("Cotización no encontrada para el par"))
    @patch('clientes.models.Cliente.objects.first')
    def test_error_moneda_invalida(self, mock_cliente_first, mock_cotizacion_get, mock_moneda_get):
        """
        Prueba que la función devuelve un error si la moneda de destino no existe.

        Configura mocks para que la moneda de origen (PYG) sea válida, pero la de destino (BTC)
        genere un error de Moneda.DoesNotExist.
        """
        mock_cliente_first.return_value = None

        # Configurar mock_moneda_get para devolver objetos específicos o lanzar excepciones
        # basándose en el 'codigo' de la moneda.
        def mock_get_moneda_side_effect(codigo):
            if codigo == 'PYG':
                # Devolver un objeto Moneda mockeado para PYG
                mock_pyg = Mock(spec=Moneda)
                mock_pyg.codigo = 'PYG'
                mock_pyg.decimales = 0
                mock_pyg.minima_denominacion = Decimal('100')
                return mock_pyg
            elif codigo == 'BTC':
                raise Moneda.DoesNotExist(f"Moneda matching query does not exist for '{codigo}'.")
            else:
                # Fallback para otras llamadas inesperadas
                raise Moneda.DoesNotExist(f"Moneda matching query does not exist for '{codigo}'.")

        mock_moneda_get.side_effect = mock_get_moneda_side_effect

        resultado = calcular_simulacion(
            monto_origen=Decimal('1000'),
            moneda_origen='PYG',
            moneda_destino='BTC', # Moneda inválida
            user=None
        )
        self.assertIsNotNone(resultado['error'])
        self.assertIn('BTC', resultado['error'])
        self.assertIn("Moneda de destino 'BTC' no encontrada.", resultado['error'])


    def test_error_transaccion_no_pyg(self):
        """
        Prueba que la función devuelve un error si la simulación no involucra PYG.

        Verifica que se genere un ValueError cuando se intenta una transacción
        directa entre dos monedas extranjeras (USD a EUR).
        """
        # No se necesita un mock explícito para Cotizacion.objects.get aquí, ya que la lógica
        # debería alcanzar el ValueError antes de intentar buscar una cotización.
        # setUpTestData asegura que los objetos Moneda 'USD' y 'EUR' existan.
        resultado = calcular_simulacion(
            monto_origen=Decimal('100'),
            moneda_origen='USD',
            moneda_destino='EUR',
            user=None
        )
        self.assertIsNotNone(resultado['error'])
        self.assertIn('La simulación debe ser entre PYG', resultado['error'])
        
# To run tests: python manage.py test core
