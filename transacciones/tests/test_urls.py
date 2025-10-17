from django.test import TestCase
from django.urls import reverse, resolve
from transacciones import views

class TransaccionesURLsTest(TestCase):

    def test_iniciar_compra_url(self):
        url = reverse('transacciones:iniciar_compra')
        self.assertEqual(url, '/transacciones/comprar/')
        self.assertEqual(resolve(url).func.view_class, views.IniciarCompraDivisaView)

    def test_iniciar_pago_url(self):
        url = reverse('transacciones:iniciar_pago', args=['12345678-1234-1234-1234-123456789012'])
        self.assertEqual(url, '/transacciones/iniciar_pago/12345678-1234-1234-1234-123456789012/')
        self.assertEqual(resolve(url).func.view_class, views.IniciarPagoTransaccionView)

    def test_webhook_pago_confirmado_url(self):
        url = reverse('transacciones:webhook_pago_confirmado')
        self.assertEqual(url, '/transacciones/webhook/pago_confirmado/')
        self.assertEqual(resolve(url).func.view_class, views.WebhookConfirmacionPagoView)

    def test_resultado_pago_url(self):
        url = reverse('transacciones:resultado_pago', args=['12345678-1234-1234-1234-123456789012'])
        self.assertEqual(url, '/transacciones/resultado/12345678-1234-1234-1234-123456789012/')
        self.assertEqual(resolve(url).func.view_class, views.ResultadoPagoView)