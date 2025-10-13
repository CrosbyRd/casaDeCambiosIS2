# simuladores/tests.py
import json
import uuid
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from transacciones.models import Transaccion
from usuarios.models import CustomUser
from clientes.models import Cliente
from monedas.models import Moneda
from operaciones.models import Tauser
from .models import PedidoPagoSimulado

class SimuladorPasarelaTests(TestCase):
    def setUp(self):
        """
        Configura el entorno inicial para cada prueba.
        Crea los objetos necesarios: usuario, cliente, monedas, tauser y una transacción.
        """
        self.client_api = Client(HTTP_ACCEPT='application/json')
        self.client_web = Client()

        # Crear usuario operador
        self.user = CustomUser.objects.create_user(
            email='operador@test.com', 
            password='password123',
            first_name='Operador',
            last_name='Test'
        )
        
        # Crear cliente
        self.cliente = Cliente.objects.create(
            nombre='Cliente de Prueba'
        )

        # Crear monedas
        self.moneda_pyg = Moneda.objects.create(codigo='PYG', nombre='Guaraní', simbolo='₲')
        self.moneda_usd = Moneda.objects.create(codigo='USD', nombre='Dólar Americano', simbolo='$')

        # Crear Tauser
        self.tauser = Tauser.objects.create(codigo_identificador='TAUSER-TEST-01', ubicacion='Oficina Matriz')

        # Crear una transacción de VENTA (cliente compra USD)
        self.transaccion = Transaccion.objects.create(
            cliente=self.cliente,
            usuario_operador=self.user,
            tipo_operacion='venta',
            estado='pendiente_pago_cliente',
            moneda_origen=self.moneda_pyg,
            monto_origen=750000,
            moneda_destino=self.moneda_usd,
            monto_destino=100,
            tasa_cambio_aplicada=7500,
            comision_aplicada=0,
            codigo_operacion_tauser='ABC123XYZ'
        )

        self.url_notificacion = 'http://testserver/webhook/notificacion'
        self.url_retorno = 'http://testserver/pago/completo'

    def test_iniciar_pago_api_exitoso(self):
        """
        Verifica que el endpoint de inicio de pago funcione correctamente con datos válidos.
        """
        url = reverse('simuladores:api_iniciar_pago')
        data = {
            "id_pedido_comercio": str(self.transaccion.id),
            "monto_total": float(self.transaccion.monto_origen),
            "comprador": {"nombre": self.cliente.nombre},
            "url_confirmacion": self.url_notificacion,
            "url_retorno": self.url_retorno
        }
        
        response = self.client_api.post(url, data=json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['respuesta'])
        self.assertIn('hash', json_response['resultado'][0])
        
        # Verificar que el pedido se creó en la BD
        self.assertTrue(PedidoPagoSimulado.objects.filter(transaccion_id=self.transaccion.id).exists())

    def test_iniciar_pago_api_transaccion_invalida(self):
        """
        Verifica que la API devuelva un error 404 si el ID de transacción no existe.
        """
        url = reverse('simuladores:api_iniciar_pago')
        data = {
            "id_pedido_comercio": str(uuid.uuid4()), # Un UUID que no existe
            "url_confirmacion": self.url_notificacion,
            "url_retorno": self.url_retorno
        }
        
        response = self.client_api.post(url, data=json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['respuesta'])

    def test_pagina_pago_simulada_vista(self):
        """
        Verifica que la página de pago se renderice correctamente.
        """
        # Primero, creamos un pedido
        pedido = PedidoPagoSimulado.objects.create(
            transaccion_id=str(self.transaccion.id),
            datos_pedido={},
            url_notificacion=self.url_notificacion,
            url_retorno=self.url_retorno
        )
        
        url = reverse('simuladores:pagina_pago', kwargs={'hash': pedido.hash})
        response = self.client_web.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simuladores/pagina_pago.html')
        # Formatear el número a dos decimales con coma para la comparación (localización 'es')
        monto_formateado = f"{self.transaccion.monto_origen:.2f}".replace('.', ',')
        self.assertContains(response, monto_formateado)

    @patch('simuladores.views.requests.post')
    def test_confirmar_pago_simulado_exitoso(self, mock_requests_post):
        """
        Verifica el flujo de confirmación de pago, incluyendo el cambio de estado,
        la llamada al webhook (mockeada) y la redirección final.
        """
        # 1. Crear el pedido simulado
        pedido = PedidoPagoSimulado.objects.create(
            transaccion_id=str(self.transaccion.id),
            datos_pedido={},
            url_notificacion=self.url_notificacion,
            url_retorno=self.url_retorno
        )

        # 2. Enviar el POST para confirmar el pago, incluyendo el método y datos adicionales
        url = reverse('simuladores:confirmar_pago', kwargs={'hash': pedido.hash})
        post_data = {
            'metodo_pago': 'transferencia_sipap',
            'datos_adicionales': '1234567890'
        }
        response = self.client_web.post(url, data=post_data)

        # 3. Verificar la redirección
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url_retorno)

        # 4. Verificar que la transacción cambió de estado
        self.transaccion.refresh_from_db()
        self.assertEqual(self.transaccion.estado, 'pendiente_retiro_tauser')

        # 5. Verificar que el pedido simulado fue eliminado
        with self.assertRaises(PedidoPagoSimulado.DoesNotExist):
            PedidoPagoSimulado.objects.get(hash=pedido.hash)

        # 6. Verificar que el webhook fue llamado correctamente
        mock_requests_post.assert_called_once()
        called_url = mock_requests_post.call_args.args[0]
        called_json = mock_requests_post.call_args.kwargs['json']
        
        self.assertEqual(called_url, self.url_notificacion)
        self.assertTrue(called_json['resultado'][0]['pagado'])
        self.assertEqual(called_json['resultado'][0]['hash_pedido'], str(pedido.hash))
        self.assertEqual(called_json['resultado'][0]['metodo_pago_simulado'], 'transferencia_sipap')
        self.assertEqual(called_json['resultado'][0]['datos_adicionales_simulados'], '1234567890')
