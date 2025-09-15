from django.test import TestCase
from pagos.forms import TipoMedioPagoForm

class TipoMedioPagoFormTests(TestCase):
    def test_form_valido(self):
        form = TipoMedioPagoForm(data={
            "nombre": "Billetera Electrónica",
            "comision_porcentaje": 2.5,
            "bonificacion_porcentaje": 1.0,
            "activo": True,
        })
        self.assertTrue(form.is_valid())

    def test_form_invalido_comision_negativa(self):
        form = TipoMedioPagoForm(data={
            "nombre": "Pago Invalido",
            "comision_porcentaje": -10,  # inválido
            "bonificacion_porcentaje": 0,
            "activo": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("comision_porcentaje", form.errors)

    def test_form_invalido_sin_nombre(self):
        form = TipoMedioPagoForm(data={
            "comision_porcentaje": 5,
            "bonificacion_porcentaje": 2,
            "activo": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)
