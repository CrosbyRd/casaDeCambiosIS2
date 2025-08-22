from django.test import TestCase
from clientes.forms import ClienteForm, ClienteSearchForm
from clientes.models import Cliente

class ClienteFormTest(TestCase):
    def test_crear_cliente_form_valido(self):
        form = ClienteForm(data={
            "nombre": "Empresa X",
            "correo_electronico": "empresa@example.com",
            "categoria": Cliente.Categoria.CORPORATIVO,
            "activo": True
        })
        self.assertTrue(form.is_valid())

    def test_email_unico(self):
        Cliente.objects.create(
            nombre="Cliente1",
            correo_electronico="duplicado@example.com"
        )
        form = ClienteForm(data={
            "nombre": "Cliente2",
            "correo_electronico": "duplicado@example.com"
        })
        self.assertFalse(form.is_valid())

    def test_valores_iniciales_para_nuevo_cliente(self):
        form = ClienteForm()
        self.assertEqual(form.fields["bonificacion_display"].initial, "0.0%")

        self.assertEqual(form.fields["limite_usd_display"].initial, "$5,000.00")

class ClienteSearchFormTest(TestCase):
    def test_form_con_datos(self):
        form = ClienteSearchForm(data={
            "q": "juan",
            "categoria": Cliente.Categoria.VIP,
            "activo": "true"
        })
        self.assertTrue(form.is_valid())
