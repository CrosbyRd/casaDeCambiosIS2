# transacciones/tests/test_models.py

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model
from monedas.models import Moneda
from configuracion.models import TransactionLimit
from transacciones.models import Transaccion

User = get_user_model()


class TransaccionModelTest(TestCase):

    def setUp(self):
        # Crear usuario de prueba (solo email, según CustomUser)
        self.cliente = User.objects.create_user(email="testuser@example.com", password="12345")

        # Crear monedas
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")

        # Crear límite de transacciones
        self.limite = TransactionLimit.objects.create(
            moneda=self.pyg,
            monto_diario=1000,
            monto_mensual=5000,
            aplica_diario=True,
            aplica_mensual=True
        )

    def test_transaccion_creacion_venta(self):
        """Verifica que se pueda crear una transacción de venta dentro del límite."""
        trans = Transaccion(
            cliente=self.cliente,
            tipo_operacion='venta',
            estado='pendiente_pago_cliente',
            moneda_origen=self.pyg,
            monto_origen=500,
            moneda_destino=self.usd,
            monto_destino=100,
            tasa_cambio_aplicada=5,
            comision_aplicada=10,
            codigo_operacion_tauser="TX001"
        )
        trans.full_clean()  # Valida límites y clean()
        trans.save()

        self.assertEqual(
            trans.estado_dinamico, 'pendiente_pago_cliente',
            msg="Error: La transacción debería estar pendiente de pago del cliente."
        )
        self.assertEqual(
            trans.get_estado_display_dinamico(), 'Pendiente de Pago del Cliente (PYG)',
            msg="Error: El display del estado dinámico no coincide con la descripción esperada."
        )

        # Error intencional: verificar que el monto_destino sea incorrecto (comentado)
        # self.assertEqual(trans.monto_destino, 999, msg="Error intencional: monto_destino no debería ser 999")

    def test_transaccion_limite_diario_excedido(self):
        """Verifica que se lance ValidationError si se excede el límite diario."""
        # Transacción previa que ocupa parte del límite
        trans1 = Transaccion(
            cliente=self.cliente,
            tipo_operacion='venta',
            estado='pendiente_pago_cliente',
            moneda_origen=self.pyg,
            monto_origen=900,
            moneda_destino=self.usd,
            monto_destino=900,
            tasa_cambio_aplicada=1,
            comision_aplicada=0,
            codigo_operacion_tauser="TX002"
        )
        trans1.full_clean()
        trans1.save()

        # Nueva transacción que excede el límite diario
        trans2 = Transaccion(
            cliente=self.cliente,
            tipo_operacion='venta',
            estado='pendiente_pago_cliente',
            moneda_origen=self.pyg,
            monto_origen=200,
            moneda_destino=self.usd,
            monto_destino=200,
            tasa_cambio_aplicada=1,
            comision_aplicada=0,
            codigo_operacion_tauser="TX003"
        )

        with self.assertRaises(ValidationError, msg="Error: Debería lanzarse ValidationError por límite diario excedido.") as cm:
            trans2.full_clean()
        
        self.assertIn("Límite diario excedido", str(cm.exception), msg="Error: El mensaje de ValidationError no contiene 'Límite diario excedido'.")

        # Error intencional: verificar un límite mensual ficticio (comentado)
        # trans2.monto_destino = 6000
        # with self.assertRaises(ValidationError):
        #     trans2.full_clean()

    def test_transaccion_estado_tasa_expirada(self):
        """Verifica que se marque la transacción como 'cancelada_tasa_expirada' si la tasa bloqueada expiró."""
        trans = Transaccion(
            cliente=self.cliente,
            tipo_operacion='compra',
            estado='pendiente_deposito_tauser',
            moneda_origen=self.usd,
            monto_origen=100,
            moneda_destino=self.pyg,
            monto_destino=500,
            tasa_cambio_aplicada=5,
            comision_aplicada=5,
            codigo_operacion_tauser="TX004",
            modalidad_tasa='bloqueada',
            tasa_garantizada_hasta=now() - timedelta(minutes=5)
        )
        trans.full_clean()
        trans.save()

        self.assertTrue(trans.is_tasa_expirada, msg="Error: La transacción debería marcarse como tasa expirada.")
        self.assertEqual(trans.estado_dinamico, 'cancelada_tasa_expirada', msg="Error: El estado dinámico debería ser 'cancelada_tasa_expirada'.")
        self.assertEqual(trans.get_estado_display_dinamico(), 'Cancelada (Tasa Expirada)', msg="Error: El display del estado dinámico no coincide con la descripción esperada.")

        # Error intencional: verificar que el estado dinámico sea 'completada' (comentado)
        # self.assertEqual(trans.estado_dinamico, 'completada', msg="Error intencional: estado dinámico no debería ser 'completada'")
