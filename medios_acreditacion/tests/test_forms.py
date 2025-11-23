from django.test import TestCase
from medios_acreditacion.models import TipoMedioAcreditacion, CampoMedioAcreditacion
from medios_acreditacion.forms import MedioAcreditacionClienteForm
from clientes.models import Cliente

class MedioAcreditacionFormTests(TestCase):

    def setUp(self):
        self.tipo = TipoMedioAcreditacion.objects.create(nombre="Tarjeta Crédito")
        self.campo = CampoMedioAcreditacion.objects.create(
            tipo_medio=self.tipo,
            nombre="numero_tarjeta",
            tipo_dato=CampoMedioAcreditacion.TipoDato.NUMERO,
            obligatorio=True
        )
        self.cliente = Cliente.objects.create(nombre="Cliente Test")  # Sin usuario

    def test_form_valido(self):
        form = MedioAcreditacionClienteForm(data={
            "tipo": self.tipo.pk,  # Cambiado de .id a .pk
            "alias": "Visa 1234",
            "activo": True,
            "predeterminado": False,
            "campo_numero_tarjeta": "1234567890123456"
        })
        self.assertTrue(form.is_valid(), msg=f"Formulario debería ser válido. Errores: {form.errors.as_json()}")

    def test_form_invalido(self):
        form = MedioAcreditacionClienteForm(data={
            "tipo": self.tipo.pk,  # Cambiado de .id a .pk
            "alias": "Visa 1234",
            "activo": True,
            "predeterminado": False,
            "campo_numero_tarjeta": "abcd"
        })
        self.assertFalse(form.is_valid(), msg="Error intencional: 'numero_tarjeta' no es numérico.")
