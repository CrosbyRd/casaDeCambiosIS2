from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from monedas.models import Moneda

User = get_user_model()

class MonedaUrlsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="testuser@example.com", password="pass123")
        self.client.force_login(self.user)
        self.moneda = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")

    def test_urls_existentes(self):
        urls = [
            reverse("monedas:listar_monedas"),
            reverse("monedas:crear_moneda"),
            reverse("monedas:editar_moneda", args=[self.moneda.id]),
            reverse("monedas:eliminar_moneda", args=[self.moneda.id]),
            reverse("monedas:moneda_detalle", args=[self.moneda.id])
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 302])
