# operaciones/tests.py

import json
import decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from transacciones.models import Transaccion
from usuarios.models import CustomUser
from monedas.models import Moneda
from cotizaciones.models import Cotizacion
from operaciones.models import Tauser

class TauserAPITests(TestCase):
    """
    Pruebas para los endpoints de la API del Tauser relacionados con GEG-105.
    """

    def setUp(self):
        """
        Configura los datos iniciales para todas las pruebas.
        """
        self.client = Client()
        self.user = CustomUser.objects.create_user(email='test@example.com', password='password', first_name="Test", last_name="User", is_active=True)
        
        self.usd = Moneda.objects.create(codigo='USD', nombre='Dólar Americano', simbolo='$')
        self.pyg = Moneda.objects.create(codigo='PYG', nombre='Guaraní', simbolo='₲')

        self.tauser = Tauser.objects.create(codigo_identificador='TAUSER-001', ubicacion='Central')

        self.cotizacion_inicial = Cotizacion.objects.create(
            moneda_base=self.usd,
            moneda_destino=self.pyg,
            valor_compra=decimal.Decimal('7500.00'),
            valor_venta=decimal.Decimal('7600.00')
        )

        # Transacción cuya tasa NO ha expirado
        self.trans_valida = Transaccion.objects.create(
            cliente=self.user,
            tipo_operacion='compra',
            estado='pendiente_deposito_tauser',
            moneda_origen=self.usd,
            monto_origen=decimal.Decimal('100.00'),
            moneda_destino=self.pyg,
            monto_destino=decimal.Decimal('750000.00'),
            tasa_cambio_aplicada=decimal.Decimal('7500.00'),
            comision_aplicada=decimal.Decimal('0.00'),
            codigo_operacion_tauser='VALIDA123',
            tasa_garantizada_hasta=timezone.now() + timedelta(hours=1)
        )

        # Transacción cuya tasa SÍ ha expirado
        self.trans_expirada = Transaccion.objects.create(
            cliente=self.user,
            tipo_operacion='compra',
            estado='pendiente_deposito_tauser',
            moneda_origen=self.usd,
            monto_origen=decimal.Decimal('100.00'),
            moneda_destino=self.pyg,
            monto_destino=decimal.Decimal('750000.00'),
            tasa_cambio_aplicada=decimal.Decimal('7500.00'),
            comision_aplicada=decimal.Decimal('0.00'),
            codigo_operacion_tauser='EXPIRA123',
            tasa_garantizada_hasta=timezone.now() - timedelta(hours=1)
        )

        self.confirmar_url = reverse('operaciones:api_confirmar_deposito_tauser')
        self.resolver_url = reverse('operaciones:api_resolver_variacion_tasa')

    # --- Pruebas para api_confirmar_deposito_tauser ---

    @patch('operaciones.views.ejecutar_acreditacion_a_cliente')
    def test_confirmar_deposito_tasa_valida(self, mock_ejecutar_acreditacion):
        """
        Verifica el "camino feliz": la tasa está garantizada y vigente.
        """
        response = self.client.post(self.confirmar_url, {'codigo_operacion': 'VALIDA123'})
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        
        self.trans_valida.refresh_from_db()
        self.assertEqual(self.trans_valida.estado, 'procesando_acreditacion')
        mock_ejecutar_acreditacion.assert_called_once_with(self.trans_valida)

    @patch('operaciones.views.ejecutar_acreditacion_a_cliente')
    def test_confirmar_deposito_tasa_expirada_sin_cambio(self, mock_ejecutar_acreditacion):
        """
        Verifica el caso donde la tasa expiró, pero el valor actual es el mismo.
        """
        response = self.client.post(self.confirmar_url, {'codigo_operacion': 'EXPIRA123'})
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        
        self.trans_expirada.refresh_from_db()
        self.assertEqual(self.trans_expirada.estado, 'procesando_acreditacion')
        mock_ejecutar_acreditacion.assert_called_once_with(self.trans_expirada)

    @patch('operaciones.views.ejecutar_acreditacion_a_cliente')
    def test_confirmar_deposito_tasa_expirada_con_cambio(self, mock_ejecutar_acreditacion):
        """
        Verifica el caso GEG-105: la tasa expiró y es diferente.
        """
        # Actualizamos la cotización para simular un cambio de tasa
        self.cotizacion_inicial.valor_compra = decimal.Decimal('7450.00')
        self.cotizacion_inicial.save()

        response = self.client.post(self.confirmar_url, {'codigo_operacion': 'EXPIRA123'})
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'requiere_confirmacion')
        self.assertEqual(decimal.Decimal(data['tasa_original']), decimal.Decimal('7500.00'))
        self.assertEqual(decimal.Decimal(data['tasa_nueva']), decimal.Decimal('7450.00'))
        
        self.trans_expirada.refresh_from_db()
        self.assertEqual(self.trans_expirada.estado, 'pendiente_deposito_tauser') # El estado no debe cambiar
        mock_ejecutar_acreditacion.assert_not_called()

    # --- Pruebas para api_resolver_variacion_tasa ---

    @patch('operaciones.views.ejecutar_acreditacion_a_cliente')
    def test_resolver_variacion_aceptar(self, mock_ejecutar_acreditacion):
        """
        Verifica que el cliente acepta la nueva tasa.
        """
        tasa_nueva = '7450.00'
        payload = {
            'codigo_operacion': 'EXPIRA123',
            'decision': 'aceptar',
            'tasa_nueva': tasa_nueva
        }
        response = self.client.post(self.resolver_url, payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        
        self.trans_expirada.refresh_from_db()
        self.assertEqual(self.trans_expirada.estado, 'procesando_acreditacion')
        self.assertEqual(self.trans_expirada.tasa_cambio_aplicada, decimal.Decimal(tasa_nueva))
        # Verificamos que el monto destino se haya recalculado
        monto_esperado = self.trans_expirada.monto_origen * decimal.Decimal(tasa_nueva)
        self.assertEqual(self.trans_expirada.monto_destino, monto_esperado)
        mock_ejecutar_acreditacion.assert_called_once_with(self.trans_expirada)

    @patch('operaciones.views.ejecutar_acreditacion_a_cliente')
    def test_resolver_variacion_cancelar(self, mock_ejecutar_acreditacion):
        """
        Verifica que el cliente cancela la transacción.
        """
        payload = {
            'codigo_operacion': 'EXPIRA123',
            'decision': 'cancelar'
        }
        response = self.client.post(self.resolver_url, payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'cancelada')
        
        self.trans_expirada.refresh_from_db()
        self.assertEqual(self.trans_expirada.estado, 'cancelada_usuario_tasa')
        
        # Verificar que el servicio de pago NO fue llamado
        mock_ejecutar_acreditacion.assert_not_called()
