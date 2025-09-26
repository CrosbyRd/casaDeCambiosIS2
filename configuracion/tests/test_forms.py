from django.test import TestCase
from configuracion.forms import TransactionLimitForm
from monedas.models import Moneda


class TransactionLimitFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear moneda base para que los defaults no exploten
        Moneda.objects.create(codigo="PYG", nombre="Guaraní")

    def test_form_valido(self):
        form = TransactionLimitForm(data={
            "aplica_diario": True,
            "monto_diario": "1500",
            "aplica_mensual": False,
            "monto_mensual": "0"
        })
        self.assertTrue(form.is_valid(), msg=f"El formulario debería ser válido. Errores: {form.errors.as_json()}")

        # ERROR INTENCIONAL: pasar texto en vez de número
        # form = TransactionLimitForm(data={
        #     "aplica_diario": True,
        #     "monto_diario": "milquinientos",  # inválido
        #     "aplica_mensual": False,
        #     "monto_mensual": "0"
        # })
        # form.is_valid()  # debería dar False


    def test_form_invalido(self):
        form = TransactionLimitForm(data={
            "aplica_diario": True,
            "monto_diario": "",   # inválido
            "aplica_mensual": True,
            "monto_mensual": "-100"  # inválido
        })
        self.assertFalse(form.is_valid(), msg="El formulario debería ser inválido por monto vacío y monto mensual negativo.")
