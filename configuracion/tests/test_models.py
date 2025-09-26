from django.test import TestCase
from configuracion.models import TransactionLimit
from monedas.models import Moneda


class TransactionLimitModelTests(TestCase):
    def setUp(self):
        self.moneda = Moneda.objects.create(nombre="Guaraní", codigo="PYG")

    def test_str_diario(self):
        limite = TransactionLimit.objects.create(
            moneda=self.moneda,
            aplica_diario=True,
            monto_diario=1000
        )
        self.assertEqual(
            str(limite),
            "PYG (Diario: 1000)",
            msg="El __str__ debería mostrar correctamente el límite diario."
        )

    def test_str_mensual(self):
        limite = TransactionLimit.objects.create(
            moneda=self.moneda,
            aplica_diario=False,
            aplica_mensual=True,
            monto_mensual=5000
        )
        self.assertEqual(
            str(limite),
            "PYG (Mensual: 5000)",
            msg="El __str__ debería mostrar correctamente el límite mensual."
        )

        # ERROR INTENCIONAL: crear límite sin monto
        # limite_err = TransactionLimit.objects.create(moneda=self.moneda, aplica_diario=True)
        # str(limite_err)  # debería explotar porque monto_diario es None


    def test_default_moneda_base(self):
        limite = TransactionLimit.objects.create(aplica_diario=True, monto_diario=2000)
        self.assertEqual(
            limite.moneda.codigo, "PYG",
            msg="El límite debería asignarse automáticamente a la moneda base PYG."
        )
