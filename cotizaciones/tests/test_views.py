from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, ContentType
from cotizaciones.models import Cotizacion
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


class CotizacionViewsTests(TestCase):
    def setUp(self):
        """
        Configuración inicial antes de cada test.
        - Se crea un usuario CustomUser con email y password.
        - Se crea un rol con permisos CRUD para Cotizacion.
        - Se crean monedas base y de destino.
        - Se crea una cotización inicial.
        - Se fuerza el login del usuario para ejecutar las pruebas autenticadas.
        """
        self.client = Client()

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_verified=True
        )

        # Crear rol con permisos CRUD de Cotizacion
        role = Role.objects.create(name="Rol Test Cotizaciones")
        content_type = ContentType.objects.get_for_model(Cotizacion)
        permisos = Permission.objects.filter(content_type=content_type)
        role.permissions.set(permisos)
        role.save()

        # Asignar el rol al usuario
        self.user.roles.add(role)
        self.user.save()

        # Crear monedas necesarias
        self.moneda_base = Moneda.objects.create(
            codigo="PYG", nombre="Guaraní", simbolo="₲"
        )
        self.moneda_destino = Moneda.objects.create(
            codigo="USD", nombre="Dólar", simbolo="$"
        )
        self.moneda_destino2 = Moneda.objects.create(
            codigo="EUR", nombre="Euro", simbolo="€"
        )

        # Crear cotización inicial
        self.cotizacion = Cotizacion.objects.create(
            moneda_base=self.moneda_base,
            moneda_destino=self.moneda_destino,
            valor_compra=7100.0,
            valor_venta=7200.0,
            comision_compra=50.0,
            comision_venta=50.0
        )

        # Forzar login
        self.client.force_login(self.user)

    def assertStatus(self, response, expected_status, custom_message=""):
        """
        Compara el código de estado HTTP de la respuesta.
        Si hay un formulario con errores, los agrega automáticamente al mensaje.
        """
        message = custom_message or (
            f"Status recibido: {response.status_code} "
            f"({HTTP_STATUS_TEXT.get(response.status_code, 'Desconocido')}). "
            f"Se esperaba: {expected_status} "
            f"({HTTP_STATUS_TEXT.get(expected_status, 'Desconocido')})."
        )

        # Agregar errores de formulario si existen
        if hasattr(response, "context") and response.context:
            form = response.context.get("form")
            if form and form.errors:
                message += f"\nErrores del formulario detectados: {form.errors.as_json()}"

        self.assertEqual(response.status_code, expected_status, msg=message)

    # --- Tests originales con fallos intencionales comentados ---
    def test_lista_cotizaciones(self):
        url = reverse("cotizaciones:cotizacion_list")
        response = self.client.get(url)
        self.assertStatus(
            response, 200, "El listado de cotizaciones no respondió como se esperaba."
        )

        # Fallo intencional comentado: URL incorrecta
        # response_error = self.client.get("/cotizaciones/lista_incorrecta/")
        # self.assertStatus(response_error, 200)

    def test_detalle_no_existe(self):
        url = reverse("cotizaciones:cotizacion_update", args=[999])
        response = self.client.get(url)
        self.assertStatus(
            response, 404, "Acceder a una cotización inexistente debería devolver 404."
        )

        # Fallo intencional comentado: GET a URL de POST
        # url_error = reverse("cotizaciones:cotizacion_delete", args=[self.cotizacion.id])
        # response_error = self.client.get(url_error)
        # self.assertStatus(response_error, 200)

    def test_crear_cotizacion(self):
        url = reverse("cotizaciones:cotizacion_create")
        data = {
            "moneda_destino": self.moneda_destino2.id,
            "valor_compra": "7300.00",
            "valor_venta": "7400.00",
            "comision_compra": "10.00",
            "comision_venta": "10.00",
        }
        response = self.client.post(url, data)

        if response.status_code != 302 and hasattr(response, "context"):
            form = response.context.get("form")
            if form:
                print("Errores del formulario:", form.errors.as_json())

        self.assertStatus(
            response, 302, "La creación de cotización debería redirigir al listado (302)."
        )

        # Fallo intencional comentado: valor negativo
        # data_error = data.copy()
        # data_error["valor_compra"] = "-100.00"
        # response_error = self.client.post(url, data_error)
        # self.assertStatus(response_error, 200)

    def test_actualizar_cotizacion(self):
        url = reverse("cotizaciones:cotizacion_update", args=[self.cotizacion.id])
        data = {
            "moneda_destino": self.moneda_destino.id,
            "valor_compra": "7150.00",
            "valor_venta": "7250.00",
            "comision_compra": "20.00",
            "comision_venta": "20.00",
        }
        response = self.client.post(url, data)
        self.assertStatus(
            response, 302, "La actualización de cotización debería redirigir al listado (302)."
        )

        # Fallo intencional comentado: campo vacío
        # data_error = data.copy()
        # data_error["valor_venta"] = ""
        # response_error = self.client.post(url, data_error)
        # self.assertStatus(response_error, 200)

    def test_eliminar_cotizacion(self):
        url = reverse("cotizaciones:cotizacion_delete", args=[self.cotizacion.id])
        response = self.client.post(url)
        self.assertStatus(
            response, 302, "La eliminación de cotización debería redirigir al listado (302)."
        )

        # Fallo intencional comentado: ID inexistente
        # url_error = reverse("cotizaciones:cotizacion_delete", args=[999])
        # response_error = self.client.post(url_error)
        # self.assertStatus(response_error, 404)

    # def test_crear_cotizacion_duplicada(self):
    #     url = reverse("cotizaciones:cotizacion_create")
    #     data = {
    #         "moneda_destino": self.moneda_destino.id,
    #         "valor_compra": "7500.00",
    #         "valor_venta": "7600.00",
    #         "comision_compra": "15.00",
    #         "comision_venta": "15.00",
    #     }
    #     response = self.client.post(url, data)
    #     self.assertStatus(
    #         response, 400, "La creación de una cotización duplicada debería fallar con Bad Request (400)."
    #     )

    def test_lista_cotizaciones_sin_login(self):
        self.client.logout()
        url = reverse("cotizaciones:cotizacion_list")
        response = self.client.get(url)
        self.assertStatus(
            response, 302, "El listado de cotizaciones requiere login. Debería redirigir al login (302)."
        )

        # Fallo intencional comentado: acceso detalle sin login
        # url_error = reverse("cotizaciones:cotizacion_update", args=[self.cotizacion.id])
        # response_error = self.client.get(url_error)
        # self.assertStatus(response_error, 302)

    def test_eliminar_cotizacion_inexistente(self):
        url = reverse("cotizaciones:cotizacion_delete", args=[999])
        response = self.client.post(url)
        self.assertStatus(
            response, 404, "La eliminación de una cotización inexistente debería devolver 404."
        )

        # Fallo intencional comentado: ID negativo
        # url_error = reverse("cotizaciones:cotizacion_delete", args=[-5])
        # response_error = self.client.post(url_error)
        # self.assertStatus(response_error, 404)
