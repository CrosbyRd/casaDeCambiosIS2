from django.test import TestCase
from django.contrib.auth import get_user_model
from django import forms  # IMPORTAR forms
from monedas.models import Moneda
from notificaciones.forms import PreferenciasNotificacionForm
from notificaciones.models import PreferenciasNotificacion

User = get_user_model()

class PreferenciasNotificacionFormTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass123")
        self.moneda = Moneda.objects.create(nombre="Dólar", codigo="USD", admite_en_linea=True)
        self.moneda2 = Moneda.objects.create(nombre="Euro", codigo="EUR", admite_en_linea=True)

    def test_form_valido_con_monedas(self):
        form_data = {
            "recibir_email_tasa_cambio": True,
            "monedas_seguidas": [self.moneda.id, self.moneda2.id]
        }
        form = PreferenciasNotificacionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_valido_sin_monedas(self):
        form_data = {
            "recibir_email_tasa_cambio": False,
            "monedas_seguidas": []
        }
        form = PreferenciasNotificacionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalido_monedas_no_existen(self):
        form_data = {
            "recibir_email_tasa_cambio": True,
            "monedas_seguidas": [99999, 88888]  # IDs que no existen
        }
        form = PreferenciasNotificacionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('monedas_seguidas', form.errors)

    def test_form_filtra_monedas_pyg(self):
        # Crear moneda PYG que debería ser excluida
        moneda_pyg = Moneda.objects.create(nombre="Guaraní", codigo="PYG", admite_en_linea=True)
        form = PreferenciasNotificacionForm()
        
        # Verificar que PYG no está en las opciones
        monedas_disponibles = list(form.fields['monedas_seguidas'].queryset)
        self.assertNotIn(moneda_pyg, monedas_disponibles)

    def test_form_filtra_monedas_no_admiten_en_linea(self):
        # Crear moneda que no admite en línea
        moneda_no_online = Moneda.objects.create(nombre="Bitcoin", codigo="BTC", admite_en_linea=False)
        form = PreferenciasNotificacionForm()
        
        # Verificar que no está en las opciones
        monedas_disponibles = list(form.fields['monedas_seguidas'].queryset)
        self.assertNotIn(moneda_no_online, monedas_disponibles)

    def test_form_etiquetas_y_widgets(self):
        form = PreferenciasNotificacionForm()
        self.assertEqual(form.fields['monedas_seguidas'].label, "Recibir notificaciones para estas monedas")
        self.assertEqual(form.fields['recibir_email_tasa_cambio'].label, "Recibir alertas de cambio de tasa por correo electrónico")
        self.assertIsInstance(form.fields['monedas_seguidas'].widget, forms.CheckboxSelectMultiple)