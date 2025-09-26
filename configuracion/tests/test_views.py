from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from configuracion.models import TransactionLimit
from monedas.models import Moneda

User = get_user_model()

HTTP_STATUS_TEXT = {
    200: "OK – Página cargada correctamente",
    302: "Found – Redirección (normalmente éxito)",
    403: "Forbidden – Acceso denegado",
    404: "Not Found – Recurso inexistente",
    400: "Bad Request – Datos inválidos en formulario",
    500: "Internal Server Error – Error del servidor",
}


class ConfiguracionViewsTests(TestCase):
    def setUp(self):
        """
        Configuración inicial:
        - Se crea un usuario de prueba y se loguea.
        - Se crea la moneda base (PYG).
        - Se inicializa el client para requests autenticados.
        """
        self.client = Client()

        # Usuario de prueba (CustomUser no acepta username)
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpass123"
        )
        self.client.force_login(self.user)

        # Moneda base
        self.moneda = Moneda.objects.create(nombre="Guaraní", codigo="PYG")

        # Límite inicial
        self.limite = TransactionLimit.objects.create(
            moneda=self.moneda,
            aplica_diario=True,
            monto_diario=5000
        )

    def assertStatus(self, response, expected_status, custom_message=""):
        """
        Compara el código de estado HTTP de la respuesta.
        Agrega mensajes personalizados en caso de error.
        """
        message = custom_message or (
            f"Status recibido: {response.status_code} "
            f"({HTTP_STATUS_TEXT.get(response.status_code, 'Desconocido')}). "
            f"Se esperaba: {expected_status} "
            f"({HTTP_STATUS_TEXT.get(expected_status, 'Desconocido')})."
        )

        # Si hay formulario con errores, los agregamos al mensaje
        if hasattr(response, "context") and response.context:
            form = response.context.get("form")
            if form and form.errors:
                message += f"\nErrores de formulario: {form.errors.as_json()}"

        self.assertEqual(response.status_code, expected_status, msg=message)

    # --- TESTS EXITOSOS ---

    def test_lista_limites(self):
        url = reverse("configuracion:lista_limites")
        response = self.client.get(url)
        self.assertStatus(response, 200, "La lista de límites debería cargar (200).")

        # ERROR INTENCIONAL: URL mal escrita
        # response = self.client.get("/configuracion/lista_limitezzz/")
        # self.assertStatus(response, 200, "Forzado: debería fallar porque la URL no existe.")

    def test_crear_limite_ok(self):
        url = reverse("configuracion:crear_limite")
        data = {
            "aplica_diario": True,
            "monto_diario": "10000",
            "aplica_mensual": False,
            "monto_mensual": "0",
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 302, "La creación de un límite válido debería redirigir (302).")

   
    def test_editar_limite_ok(self):
        url = reverse("configuracion:editar_limite", args=[self.limite.id])
        data = {
            "aplica_diario": True,
            "monto_diario": "15000",
            "aplica_mensual": False,
            "monto_mensual": "0",
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 302, "La edición de un límite válido debería redirigir (302).")

       
    def test_eliminar_limite_ok(self):
        url = reverse("configuracion:eliminar_limite", args=[self.limite.id])
        response = self.client.post(url)
        self.assertStatus(response, 302, "La eliminación debería redirigir al listado (302).")

      