from django.test import TestCase
from monedas.forms import MonedaForm

class MonedaFormTests(TestCase):

    def test_form_valido_autocompleta_nombre_simbolo(self):
        # Usar un código que no esté en la base de datos de prueba para evitar conflicto unique
        data = {
            "codigo": "EUR",
            "nombre": "Euro",                # obligatorio
            "simbolo": "€",                  # obligatorio
            "decimales": 2,
            "minima_denominacion": 1,
            "admite_en_linea": True,
            "admite_terminal": True
        }
        form = MonedaForm(data)
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)
        self.assertEqual(instance.nombre, "Euro")
        self.assertEqual(instance.simbolo, "€")

    def test_form_minima_denominacion_invalida(self):
        data = {
            "codigo": "PYG",
            "nombre": "Guaraní",             # obligatorio
            "simbolo": "₲",                  # obligatorio
            "decimales": 2,
            "minima_denominacion": 0,
            "admite_en_linea": True,
            "admite_terminal": True
        }
        form = MonedaForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("minima_denominacion", form.errors)
