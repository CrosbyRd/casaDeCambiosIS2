from django.test import TestCase
from ted.forms import AjusteInventarioForm
from monedas.models import TedMovimiento

class AjusteInventarioFormTests(TestCase):
    def test_form_valid_data(self):
        data = {
            'delta': 10,
            'motivo': TedMovimiento.MOTIVO_AJUSTE,
            'comentario': 'Ingreso de billetes',
            'confirm': True
        }
        form = AjusteInventarioForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_confirm(self):
        data = {
            'delta': 5,
            'motivo': TedMovimiento.MOTIVO_OTRO,
            'comentario': 'Prueba sin confirmar',
        }
        form = AjusteInventarioForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('confirm', form.errors)

    def test_form_invalid_without_delta(self):
        data = {
            'motivo': TedMovimiento.MOTIVO_AJUSTE,
            'confirm': True
        }
        form = AjusteInventarioForm(data=data)
        self.assertFalse(form.is_valid())

    def test_help_texts(self):
        form = AjusteInventarioForm()
        self.assertIn('Usa valores positivos', form.fields['delta'].help_text)

    def test_choices_motivo(self):
        form = AjusteInventarioForm()
        self.assertTrue(len(form.fields['motivo'].choices) >= 2)
