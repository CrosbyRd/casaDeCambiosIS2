from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json
from unittest.mock import patch, MagicMock

from monedas.models import Moneda
from clientes.models import Cliente
from pagos.models import TipoMedioPago
from transacciones.models import Transaccion
from transacciones.views import (
    IniciarCompraDivisaView,
    IniciarPagoTransaccionView,
    WebhookConfirmacionPagoView,
    ResultadoPagoView
)

User = get_user_model()

class TransaccionesViewsTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        
        # Crear usuarios
        self.user = User.objects.create_user(
            email="cliente@test.com", 
            password="pass123"
        )
        self.operador = User.objects.create_user(
            email="operador@test.com", 
            password="pass123"
        )
        
        # Crear cliente usando la estructura REAL
        self.cliente = Cliente.objects.create(
            nombre="Cliente de Prueba",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        
        # Crear monedas
        self.moneda_pyg = Moneda.objects.create(
            nombre="Guaraní", 
            codigo="PYG", 
            admite_en_linea=True
        )
        self.moneda_usd = Moneda.objects.create(
            nombre="Dólar", 
            codigo="USD", 
            admite_en_linea=True
        )
        
        # Crear medio de pago usando la estructura REAL
        self.medio_pago = TipoMedioPago.objects.create(
            nombre="Tarjeta de Crédito",
            comision_porcentaje=2.5,
            descripcion="Medio de pago de prueba",
            activo=True,
            engine='stripe'
        )
        
        # Crear transacción de prueba
        self.transaccion = Transaccion.objects.create(
            cliente=self.cliente,
            usuario_operador=self.operador,
            tipo_operacion='venta',
            estado='pendiente_pago_cliente',
            moneda_origen=self.moneda_pyg,
            monto_origen=100000,
            moneda_destino=self.moneda_usd,
            monto_destino=14.28,
            tasa_cambio_aplicada=7000,
            comision_aplicada=1000,
            medio_pago_utilizado=self.medio_pago,
            modalidad_tasa='bloqueada',
            tasa_garantizada_hasta=timezone.now() + timedelta(hours=1),
            codigo_operacion_tauser="TEST001"
        )

    def test_iniciar_compra_divisa_view_get(self):
        """Test para la vista IniciarCompraDivisaView (GET)"""
        request = self.factory.get(reverse('transacciones:iniciar_compra'))
        request.user = self.user
        
        view = IniciarCompraDivisaView()
        view.setup(request)
        
        response = view.get(request)
        self.assertEqual(response.status_code, 200)
        # Corregir la comparación del template_name
        self.assertEqual(response.template_name[0], 'transacciones/iniciar_compra_divisa.html')

    @patch('transacciones.views.iniciar_cobro_a_cliente')
    @patch('transacciones.views.get_cliente_activo')
    def test_iniciar_pago_transaccion_view_success(self, mock_get_cliente, mock_iniciar_cobro):
        """Test exitoso para IniciarPagoTransaccionView"""
        mock_get_cliente.return_value = self.cliente
        mock_iniciar_cobro.return_value = 'https://pasarela.pago.com/pago123'
        
        url = reverse('transacciones:iniciar_pago', args=[self.transaccion.id])
        request = self.factory.post(url)
        request.user = self.user
        
        # Agregar middleware de mensajes
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
        
        response = IniciarPagoTransaccionView.as_view()(request, transaccion_id=self.transaccion.id)
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(response.url, 'https://pasarela.pago.com/pago123')

    @patch('transacciones.views.get_cliente_activo')
    def test_iniciar_pago_transaccion_view_invalid_state(self, mock_get_cliente):
        """Test para transacción en estado inválido"""
        mock_get_cliente.return_value = self.cliente
        
        # Cambiar estado a uno inválido
        self.transaccion.estado = 'completada'
        self.transaccion.save()
        
        url = reverse('transacciones:iniciar_pago', args=[self.transaccion.id])
        request = self.factory.post(url)
        request.user = self.user
        
        # Agregar middleware de mensajes
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
        
        response = IniciarPagoTransaccionView.as_view()(request, transaccion_id=self.transaccion.id)
        
        self.assertEqual(response.status_code, 302)  # Redirect con mensaje de error

    @patch('transacciones.views.get_cliente_activo')
    def test_iniciar_pago_transaccion_view_flotante_tasa(self, mock_get_cliente):
        """Test para transacción con tasa flotante"""
        mock_get_cliente.return_value = self.cliente
        
        # Crear transacción con tasa flotante
        transaccion_flotante = Transaccion.objects.create(
            cliente=self.cliente,
            usuario_operador=self.operador,
            tipo_operacion='venta',
            estado='pendiente_pago_cliente',
            moneda_origen=self.moneda_pyg,
            monto_origen=100000,
            moneda_destino=self.moneda_usd,
            monto_destino=14.28,
            tasa_cambio_aplicada=7000,
            comision_aplicada=1000,
            medio_pago_utilizado=self.medio_pago,
            modalidad_tasa='flotante',
            codigo_operacion_tauser="TEST002"
        )
        
        url = reverse('transacciones:iniciar_pago', args=[transaccion_flotante.id])
        request = self.factory.post(url)
        request.user = self.user
        
        # Agregar middleware de mensajes
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
        
        # CORREGIDO: Usar el path correcto según views.py (cotizaciones.models.Cotizacion)
        with patch('cotizaciones.models.Cotizacion') as mock_cotizacion:
            mock_cotizacion_instance = MagicMock()
            mock_cotizacion_instance.total_venta = 7100  # Nueva tasa
            mock_cotizacion.objects.get.return_value = mock_cotizacion_instance
            
            with patch('transacciones.views.iniciar_cobro_a_cliente') as mock_iniciar_cobro:
                mock_iniciar_cobro.return_value = 'https://pasarela.pago.com/pago123'
                
                response = IniciarPagoTransaccionView.as_view()(request, transaccion_id=transaccion_flotante.id)
                
                # Verificar que se actualizó la tasa
                transaccion_flotante.refresh_from_db()
                self.assertEqual(transaccion_flotante.tasa_cambio_aplicada, 7100)

    @patch('pagos.services.handle_payment_webhook')
    def test_webhook_confirmacion_pago_view_success(self, mock_handle_webhook):
        """Test exitoso para WebhookConfirmacionPagoView"""
        mock_handle_webhook.return_value = {
            'status': 'OK',
            'message': 'Webhook procesado correctamente'
        }
        
        webhook_data = {
            'referencia_comercio': str(self.transaccion.id),
            'estado': 'aprobado',
            'monto': '100000'
        }
        
        request = self.factory.post(
            reverse('transacciones:webhook_pago_confirmado'),
            data=json.dumps(webhook_data),
            content_type='application/json'
        )
        
        response = WebhookConfirmacionPagoView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'ok')

    def test_webhook_confirmacion_pago_view_invalid_json(self):
        """Test para webhook con JSON inválido"""
        request = self.factory.post(
            reverse('transacciones:webhook_pago_confirmado'),
            data='invalid json',
            content_type='application/json'
        )
        
        response = WebhookConfirmacionPagoView.as_view()(request)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Cuerpo de la petición inválido.')

    @patch('pagos.services.handle_payment_webhook')
    def test_webhook_confirmacion_pago_view_error(self, mock_handle_webhook):
        """Test para webhook con error en el procesamiento"""
        mock_handle_webhook.return_value = {
            'status': 'ERROR',
            'message': 'Error al procesar el pago'
        }
        
        webhook_data = {
            'referencia_comercio': str(self.transaccion.id),
            'estado': 'rechazado'
        }
        
        request = self.factory.post(
            reverse('transacciones:webhook_pago_confirmado'),
            data=json.dumps(webhook_data),
            content_type='application/json'
        )
        
        response = WebhookConfirmacionPagoView.as_view()(request)
        
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)

    def test_resultado_pago_view_get_context(self):
        """Test para ResultadoPagoView (GET)"""
        url = reverse('transacciones:resultado_pago', args=[self.transaccion.id])
        request = self.factory.get(url)
        request.user = self.user
        
        response = ResultadoPagoView.as_view()(request, transaccion_id=self.transaccion.id)
        
        self.assertEqual(response.status_code, 200)
        # Corregir la comparación del template_name
        self.assertEqual(response.template_name[0], 'transacciones/resultado_pago.html')

    @patch('transacciones.views.iniciar_cobro_a_cliente')
    def test_resultado_pago_view_with_continuar_pago(self, mock_iniciar_cobro):
        """Test para ResultadoPagoView con opción de continuar pago"""
        mock_iniciar_cobro.return_value = 'https://pasarela.pago.com/continuar'
        
        url = reverse('transacciones:resultado_pago', args=[self.transaccion.id])
        request = self.factory.get(url)
        request.user = self.user
        
        response = ResultadoPagoView.as_view()(request, transaccion_id=self.transaccion.id)
        
        self.assertEqual(response.status_code, 200)
        # Verificar que el contexto tiene la URL para continuar el pago
        self.assertEqual(response.context_data['transaccion'], self.transaccion)

    def test_resultado_pago_view_transaccion_no_existe(self):
        """Test para ResultadoPagoView con transacción que no existe"""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        url = reverse('transacciones:resultado_pago', args=[fake_uuid])
        request = self.factory.get(url)
        request.user = self.user
        
        with self.assertRaises(Exception):  # Debería lanzar 404
            ResultadoPagoView.as_view()(request, transaccion_id=fake_uuid)