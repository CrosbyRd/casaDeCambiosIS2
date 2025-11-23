from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, ContentType
from monedas.models import Moneda
from roles.models import Role

User = get_user_model()

HTTP_STATUS_TEXT = {
    200: "Página cargada correctamente (con formulario y/o errores)",
    302: "Redirección a otra página (normalmente éxito de creación/edición/eliminación)",
    403: "Acceso prohibido (usuario sin permisos)",
    404: "Página o recurso no encontrado",
    400: "Solicitud inválida (Bad Request, datos incorrectos en formulario)",
    500: "Error interno del servidor"
}

class MonedaViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            email="testuser_monedas@example.com",
            password="testpass123",
            first_name="Test",
            last_name="UserMonedas",
            is_active=True,
            is_verified=True
        )

        # Crear rol con permisos de monedas
        role = Role.objects.create(name="Rol Test Monedas")
        content_type = ContentType.objects.get_for_model(Moneda)
        permisos = Permission.objects.filter(content_type=content_type)
        role.permissions.set(permisos)
        role.save()

        self.user.roles.add(role)
        self.user.save()

        # Crear monedas iniciales
        self.moneda1 = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="$")
        self.moneda2 = Moneda.objects.create(codigo="PYG", nombre="Guaraní", simbolo="₲")

        # Forzar login
        self.client.force_login(self.user)

    def assertStatus(self, response, expected_status, custom_message=""):
        message = custom_message or (
            f"Status recibido: {response.status_code} "
            f"({HTTP_STATUS_TEXT.get(response.status_code, 'Desconocido')}). "
            f"Se esperaba: {expected_status} "
            f"({HTTP_STATUS_TEXT.get(expected_status, 'Desconocido')})."
        )
        if hasattr(response, "context") and response.context:
            form = response.context.get("form")
            if form and form.errors:
                message += f"\nErrores del formulario detectados: {form.errors.as_json()}"
        self.assertEqual(response.status_code, expected_status, msg=message)

    # --- TESTS ---

    def test_listar_monedas(self):
        url = reverse("monedas:listar_monedas")
        response = self.client.get(url)
        self.assertStatus(response, 200, "El listado de monedas debería responder con 200.")

    def test_moneda_detalle(self):
        url = reverse("monedas:moneda_detalle", args=[self.moneda1.id])
        response = self.client.get(url)
        self.assertStatus(response, 200, "Detalle de moneda debería cargar correctamente (200).")

    def test_moneda_detalle_inexistente(self):
        url = reverse("monedas:moneda_detalle", args=[999])
        response = self.client.get(url)
        self.assertStatus(response, 404, "Acceder a moneda inexistente debería devolver 404.")

    def test_crear_moneda(self):
        url = reverse("monedas:crear_moneda")
        data = {
            "codigo": "EUR",  # <- usar código único
            "nombre": "Euro",  # <- agregar
            "simbolo": "€",    # <- agregar
            "decimales": 2,
            "minima_denominacion": 1,
            "admite_en_linea": True,
            "admite_terminal": True,
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 302, "La creación de moneda debería redirigir al listado (302).")

    def test_editar_moneda(self):
        url = reverse("monedas:editar_moneda", args=[self.moneda1.id])
        data = {
            "codigo": "USD",
            "nombre": "Dólar estadounidense",  # <- agregar
            "simbolo": "$",                     # <- agregar
            "decimales": 2,
            "minima_denominacion": 5,
            "admite_en_linea": True,
            "admite_terminal": False,
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 302, "La edición de moneda debería redirigir al listado (302).")

    def test_eliminar_moneda(self):
        url = reverse("monedas:eliminar_moneda", args=[self.moneda2.id])
        response = self.client.post(url)
        self.assertStatus(response, 302, "La eliminación de moneda debería redirigir al listado (302).")

    def test_listar_monedas_sin_login(self):
        self.client.logout()
        url = reverse("monedas:listar_monedas")
        response = self.client.get(url)
        self.assertStatus(response, 302, "El listado de monedas requiere login. Debería redirigir al login (302).")
