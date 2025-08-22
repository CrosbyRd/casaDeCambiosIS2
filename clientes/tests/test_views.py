from django.test import TestCase
from django.urls import reverse
from clientes.models import Cliente

class ClienteViewsTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Juan Test",
            correo_electronico="test@example.com"
        )

    def test_list_view(self):
        response = self.client.get(reverse("clientes:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Juan Test")

    def test_detail_view(self):
        response = self.client.get(reverse("clientes:detalle", args=[self.cliente.id_cliente]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test@example.com")

    def test_create_view(self):
        response = self.client.post(reverse("clientes:crear"), {
            "nombre": "Nuevo Cliente",
            "correo_electronico": "nuevo@example.com",
            "categoria": Cliente.Categoria.MINORISTA,
            "activo": True
        })
        self.assertEqual(response.status_code, 302)  # Redirección tras crear
        self.assertTrue(Cliente.objects.filter(correo_electronico="nuevo@example.com").exists())

    def test_update_view(self):
        response = self.client.post(reverse("clientes:editar", args=[self.cliente.id_cliente]), {
            "nombre": "Juan Editado",
            "correo_electronico": "test@example.com",
            "categoria": Cliente.Categoria.MINORISTA,
            "activo": True
        })
        self.assertEqual(response.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, "Juan Editado")

    def test_delete_view(self):
        response = self.client.post(reverse("clientes:eliminar", args=[self.cliente.id_cliente]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Cliente.objects.filter(id_cliente=self.cliente.id_cliente).exists())

    def test_toggle_estado(self):
        estado_inicial = self.cliente.activo
        response = self.client.get(reverse("clientes:toggle_estado", args=[self.cliente.id_cliente]))
        self.assertEqual(response.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertNotEqual(self.cliente.activo, estado_inicial)
