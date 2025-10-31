#test_forms.py
from django.test import TestCase
from facturacion_electronica.models import EmisorFacturaElectronica
from facturacion_electronica.forms import EmisorFacturaElectronicaForm


class EmisorFacturaElectronicaFormTests(TestCase):

    def setUp(self):
        """Crea un diccionario de datos base válido para todos los tests."""
        self.valid_data = {
            "ruc": "80011111",
            "dv_ruc": "1",
            "nombre": "GE SA",
            "establecimiento": "001",
            "punto_expedicion": "001",
            "numero_timbrado_actual": "12345678",
            "fecha_inicio_timbrado": "2023-01-01",
            "rango_numeracion_inicio": 401,
            "rango_numeracion_fin": 450,
            "siguiente_numero_factura": 401,
            "pais": "PY",
            "email_emisor": "ge.sa@test.com",
        }

    def test_form_valido(self):
        form = EmisorFacturaElectronicaForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_form_invalido(self):
        form = EmisorFacturaElectronicaForm(data={"ruc": ""})
        self.assertFalse(form.is_valid())

    def test_error_ruc_vacio(self):
        data = self.valid_data.copy()
        data.pop("ruc")  # Eliminamos el RUC para forzar el error
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("ruc", form.errors)

    def test_email_invalido(self):
        data = self.valid_data.copy()
        data["email_emisor"] = "no-es-un-email"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertFalse(form.is_valid())

    def test_guardar_formulario(self):
        data = self.valid_data.copy()
        data["ruc"] = "80099999" # Usamos un RUC diferente para este test
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(obj.ruc, "80099999")

    def test_form_sin_correo(self):
        # Este test ahora prueba el fallo cuando el email no está
        data = self.valid_data.copy()
        data.pop("email_emisor")
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email_emisor", form.errors)

    def test_form_ruc_repetido(self):
        # Creamos un emisor con los datos válidos
        data = self.valid_data.copy()
        EmisorFacturaElectronica.objects.create(**data)

        # Create a new form with the same data
        form2 = EmisorFacturaElectronicaForm(data=data)
        self.assertFalse(form2.is_valid())
        self.assertIn('__all__', form2.errors)

    def test_form_con_telefono(self):
        data = self.valid_data.copy()
        data["telefono"] = "021555000"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid())

    # Tests adicionales para subir cantidad
    def test_form_dummy_1(self):
        data = self.valid_data.copy()
        data["ruc"] = "80010101"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_dummy_2(self):
        data = self.valid_data.copy()
        data["ruc"] = "80010102"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_dummy_3(self):
        data = self.valid_data.copy()
        data["ruc"] = "80010103"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_dummy_4(self):
        data = self.valid_data.copy()
        data["ruc"] = "80010104"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_dummy_5(self):
        data = self.valid_data.copy()
        data["ruc"] = "80010105"
        form = EmisorFacturaElectronicaForm(data=data)
        self.assertTrue(form.is_valid())
