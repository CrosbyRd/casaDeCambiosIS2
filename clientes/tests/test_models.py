from django.test import TestCase
from clientes.models import Cliente
from decimal import Decimal

class ClienteModelTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Juan Pérez",
            correo_electronico="juan@example.com",
            categoria=Cliente.Categoria.VIP,
            activo=True
        )

    def test_str(self):
        self.assertEqual(
            str(self.cliente),
            "Juan Pérez (juan@example.com) - VIP"
        )

    def test_bonificacion_vip(self):
        self.assertEqual(self.cliente.bonificacion, Decimal("10.0"))

    def test_limite_compra_usd_vip(self):
        self.assertEqual(self.cliente.limite_compra_usd, Decimal("50000.00"))

    def test_esta_activo(self):
        self.assertTrue(self.cliente.esta_activo())

    def test_puede_comprar_dentro_del_limite(self):
        puede, msg = self.cliente.puede_comprar("USD", Decimal("1000"))
        self.assertTrue(puede)
        self.assertIn("50000.00", msg)

    def test_puede_comprar_fuera_del_limite(self):
        puede, msg = self.cliente.puede_comprar("USD", Decimal("60000"))
        self.assertFalse(puede)
