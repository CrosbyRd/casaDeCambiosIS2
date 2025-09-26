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
from django.utils import timezone # Importar timezone
from datetime import timedelta # Importar timedelta
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


class SimulacionLogicConcrectTest(TestCase):
    """
    Conjunto de pruebas para la función `calcular_simulacion` utilizando
    datos reales en la base de datos de prueba para verificar los cálculos
    específicos de la lógica de negocio.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Configura los datos de prueba necesarios para los escenarios de negocio.
        """
        # Crear Monedas
        cls.pyg = Moneda.objects.create(codigo='PYG', nombre='Guaraní', decimales=0)
        cls.usd = Moneda.objects.create(codigo='USD', nombre='Dólar', decimales=2)

        # Crear Usuarios
        cls.user_vip = User.objects.create_user(
            email='vip@example.com',
            password='password',
            first_name='Vip',
            last_name='User'
        )
        cls.user_corp = User.objects.create_user(
            email='corp@example.com',
            password='password',
            first_name='Corp',
            last_name='User'
        )

        # Crear Clientes y asociarlos a los usuarios
        cls.cliente_vip = Cliente.objects.create(
            nombre='Cliente VIP de Prueba',
            categoria=Cliente.Categoria.VIP
        )
        cls.user_vip.clientes.add(cls.cliente_vip)

        cls.cliente_corp = Cliente.objects.create(
            nombre='Cliente Corporativo de Prueba',
            categoria=Cliente.Categoria.CORPORATIVO
        )
        cls.user_corp.clientes.add(cls.cliente_corp)

        # Crear Cotización con los valores del ejemplo
        # PB_DOLAR = 7.300, COMISION_VTA = 100, COMISION_COM = 50
        Cotizacion.objects.create(
            moneda_base=cls.pyg,
            moneda_destino=cls.usd,
            valor_venta=Decimal('7300'),
            comision_venta=Decimal('100'),
            valor_compra=Decimal('7300'),
            comision_compra=Decimal('50')
        )

    def test_venta_a_cliente_vip(self):
        """
        Verifica el cálculo de venta de 1000 USD a un cliente VIP.
        Fórmula: DOLARES = GUARANIES / (PB_DOLAR + COMISION_VTA - (COMISION_VTA * 10%))
        TC_VTA_VIP = 7300 + 100 - (100 * 0.10) = 7390
        GUARANIES para 1000 USD = 1000 * 7390 = 7,390,000
        """
        monto_pyg = Decimal('7390000')
        resultado = calcular_simulacion(
            monto_origen=monto_pyg,
            moneda_origen='PYG',
            moneda_destino='USD',
            user=self.user_vip
        )

        self.assertIsNone(resultado['error'])
        # La bonificación es el 10% de la comisión de 100 = 10
        self.assertEqual(resultado['bonificacion_aplicada'], Decimal('10.0'))
        # La tasa aplicada es 7300 + 100 - 10 = 7390
        self.assertEqual(resultado['tasa_aplicada'], Decimal('7390.0'))
        # El monto recibido debe ser 7,390,000 / 7390 = 1000
        self.assertEqual(resultado['monto_recibido'], Decimal('1000.00'))

    def test_compra_a_cliente_corporativo(self):
        """
        Verifica el cálculo de compra de 1000 USD a un cliente Corporativo.
        Fórmula: GUARANIES = DOLARES * (PB_DOLAR - (COMISION_COM - (COMISION_COM * 5%)))
        COMISION_FINAL = 50 - (50 * 0.05) = 50 - 2.5 = 47.5
        TC_COMP_CORP = 7300 - 47.5 = 7252.5
        GUARANIES por 1000 USD = 1000 * 7252.5 = 7,252,500
        """
        monto_usd = Decimal('1000')
        resultado = calcular_simulacion(
            monto_origen=monto_usd,
            moneda_origen='USD',
            moneda_destino='PYG',
            user=self.user_corp
        )

        self.assertIsNone(resultado['error'])
        # La bonificación (descuento en comisión) es 5% de 50 = 2.5
        self.assertEqual(resultado['bonificacion_aplicada'], Decimal('2.5'))
        # La tasa aplicada es 7300 - (50 - 2.5) = 7252.5
        self.assertEqual(resultado['tasa_aplicada'], Decimal('7252.5'))
        # El monto recibido debe ser 1000 * 7252.5 = 7,252,500
        self.assertEqual(resultado['monto_recibido'], Decimal('7252500'))


from django.urls import reverse
from django.test import Client
from transacciones.models import Transaccion

class CoreViewsTest(TestCase):
    """
    Pruebas para las vistas en la app `core` que manejan el flujo de operaciones.
    """
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='testuser@example.com', password='password', is_active=True)
        cls.cliente = Cliente.objects.create(nombre='Test Client')
        cls.user.clientes.add(cls.cliente)
        
        cls.pyg = Moneda.objects.create(codigo='PYG', nombre='Guaraní')
        cls.usd = Moneda.objects.create(codigo='USD', nombre='Dólar')
        
        Cotizacion.objects.create(
            moneda_base=cls.pyg,
            moneda_destino=cls.usd,
            valor_venta=Decimal('7400'),
            comision_venta=Decimal('100'),
            valor_compra=Decimal('7300'),
            comision_compra=Decimal('50')
        )

    def setUp(self):
        self.client = Client()
        self.client.login(email='testuser@example.com', password='password')

    def test_confirmar_operacion_crea_transaccion_con_bloqueo_tasa(self):
        """
        Verifica que la vista `confirmar_operacion` crea una transacción de tipo 'compra'
        (cliente vende USD) y establece correctamente el campo `tasa_garantizada_hasta`.
        """
        # 1. Simular los datos que la vista `iniciar_operacion` guardaría en la sesión
        session = self.client.session
        session['operacion_pendiente'] = {
            'tipo_operacion': 'compra', # Cliente vende USD
            'moneda_origen_codigo': 'USD',
            'monto_origen': '100.00',
            'moneda_destino_codigo': 'PYG',
            'monto_recibido': '725000.00', # (7300 - 50) * 100
            'tasa_aplicada': '7250.00',
            'comision_aplicada': '0.00', # Simplificado para la prueba
        }
        session.save()

        # 2. Realizar el POST a la vista de confirmación
        url = reverse('core:confirmar_operacion')
        response = self.client.post(url)

        # 3. Verificar la redirección y la creación del objeto
        self.assertEqual(response.status_code, 302)
        # La redirección ahora va a la página de detalle de la operación
        transaccion_id = Transaccion.objects.first().id # Obtener el ID de la transacción creada
        self.assertRedirects(response, reverse('core:detalle_operacion_tauser', args=[transaccion_id]))

        # 4. Comprobar que la transacción se creó con los datos correctos
        self.assertTrue(Transaccion.objects.exists())
        transaccion = Transaccion.objects.first()
        
        self.assertEqual(transaccion.cliente, self.user)
        self.assertEqual(transaccion.tipo_operacion, 'compra')
        self.assertEqual(transaccion.estado, 'pendiente_deposito_tauser')
        self.assertIsNotNone(transaccion.tasa_garantizada_hasta)

        # 5. Verificar que la fecha de garantía sea aproximadamente 2 horas en el futuro
        ahora = timezone.now()
        dos_horas_despues = ahora + timedelta(hours=2)
        diferencia = dos_horas_despues - transaccion.tasa_garantizada_hasta
        
        # Permitimos una pequeña diferencia (ej. 5 segundos) para la ejecución del código
        self.assertTrue(abs(diferencia.total_seconds()) < 5)

    def test_confirmar_operacion_crea_transaccion_venta_con_bloqueo_tasa_15min(self):
        """
        Verifica que la vista `confirmar_operacion` crea una transacción de tipo 'venta'
        (cliente compra USD) y establece `tasa_garantizada_hasta` a 15 minutos.
        """
        # 1. Simular los datos que la vista `iniciar_operacion` guardaría en la sesión
        session = self.client.session
        session['operacion_pendiente'] = {
            'tipo_operacion': 'venta', # Cliente compra USD
            'moneda_origen_codigo': 'PYG',
            'monto_origen': '740000.00',
            'moneda_destino_codigo': 'USD',
            'monto_recibido': '100.00',
            'tasa_aplicada': '7400.00',
            'comision_aplicada': '0.00', # Simplificado para la prueba
        }
        session.save()

        # 2. Realizar el POST a la vista de confirmación
        url = reverse('core:confirmar_operacion')
        response = self.client.post(url)

        # 3. Verificar la redirección y la creación del objeto
        self.assertEqual(response.status_code, 302)
        transaccion_id = Transaccion.objects.first().id
        self.assertRedirects(response, reverse('core:detalle_operacion_tauser', args=[transaccion_id]))

        # 4. Comprobar que la transacción se creó con los datos correctos
        self.assertTrue(Transaccion.objects.exists())
        transaccion = Transaccion.objects.first()
        
        self.assertEqual(transaccion.cliente, self.user)
        self.assertEqual(transaccion.tipo_operacion, 'venta')
        self.assertEqual(transaccion.estado, 'pendiente_pago_cliente')
        self.assertIsNotNone(transaccion.tasa_garantizada_hasta)

        # 5. Verificar que la fecha de garantía sea aproximadamente 15 minutos en el futuro
        ahora = timezone.now()
        quince_minutos_despues = ahora + timedelta(minutes=15)
        diferencia = quince_minutos_despues - transaccion.tasa_garantizada_hasta
        
        # Permitimos una pequeña diferencia (ej. 5 segundos) para la ejecución del código
        self.assertTrue(abs(diferencia.total_seconds()) < 5)
