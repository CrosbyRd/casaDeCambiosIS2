from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, ContentType
from pagos.models import TipoMedioPago
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


class PagosViewsTests(TestCase):
    def setUp(self):
        """
        Configuración inicial antes de cada test.
        - Se crea un usuario CustomUser con email y password.
        - Se crea un rol con permisos CRUD para TipoMedioPago.
        - Se crea un TipoMedioPago inicial.
        - Se fuerza el login del usuario para ejecutar las pruebas autenticadas.
        """
        self.client = Client()

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            email="testuser_pagos@example.com",
            password="testpass123",
            first_name="Test",
            last_name="UserPagos",
            is_active=True,
            is_verified=True
        )

        # Crear rol con permisos CRUD de TipoMedioPago
        role = Role.objects.create(name="Rol Test Pagos")
        content_type = ContentType.objects.get_for_model(TipoMedioPago)
        permisos = Permission.objects.filter(content_type=content_type)
        role.permissions.set(permisos)
        role.save()

        # Asignar el rol al usuario
        self.user.roles.add(role)
        self.user.save()

        # Crear TipoMedioPago inicial
        self.tipo_pago = TipoMedioPago.objects.create(
            nombre="Tarjeta de Crédito",
            comision_porcentaje=5.0,
            bonificacion_porcentaje=0.0,
            activo=True
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

    # --- TESTS ---

    def test_listar_tipos_medio_pago(self):
        url = reverse("pagos:listar_tipos_medio_pago")
        response = self.client.get(url)
        self.assertStatus(response, 200, "El listado de tipos de medios de pago debería responder con 200.")

    def test_ver_tipo_medio_pago(self):
        url = reverse("pagos:ver_tipo_medio_pago", args=[self.tipo_pago.id])
        response = self.client.get(url)
        self.assertStatus(response, 200, "La vista detalle debería cargar correctamente (200).")

    def test_ver_tipo_medio_pago_inexistente(self):
        url = reverse("pagos:ver_tipo_medio_pago", args=[999])
        response = self.client.get(url)
        self.assertStatus(response, 404, "Intentar ver un TipoMedioPago inexistente debería devolver 404.")

    def test_agregar_tipo_medio_pago(self):
        url = reverse("pagos:agregar_tipo_medio_pago")
        data = {
            "nombre": "Billetera Electrónica",
            "comision_porcentaje": "2.50",
            "bonificacion_porcentaje": "1.00",
            "activo": True,
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 302, "La creación de TipoMedioPago debería redirigir al listado (302).")

    def test_agregar_tipo_medio_pago_invalido(self):
        url = reverse("pagos:agregar_tipo_medio_pago")
        data = {
            "nombre": "",  # inválido
            "comision_porcentaje": "-5",  # inválido
            "bonificacion_porcentaje": "150",  # inválido
            "activo": True,
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 200, "La creación con datos inválidos debería quedarse en el formulario (200).")

    def test_editar_tipo_medio_pago(self):
        url = reverse("pagos:editar_tipo_medio_pago", args=[self.tipo_pago.id])
        data = {
            "nombre": "Tarjeta Débito",
            "comision_porcentaje": "3.00",
            "bonificacion_porcentaje": "0.50",
            "activo": True,
        }
        response = self.client.post(url, data)
        self.assertStatus(response, 302, "La edición debería redirigir al listado (302).")

    def test_eliminar_tipo_medio_pago(self):
        url = reverse("pagos:eliminar_tipo_medio_pago", args=[self.tipo_pago.id])
        response = self.client.post(url)
        self.assertStatus(response, 302, "La eliminación debería redirigir al listado (302).")

    def test_eliminar_tipo_medio_pago_inexistente(self):
        url = reverse("pagos:eliminar_tipo_medio_pago", args=[999])
        response = self.client.post(url)
        self.assertStatus(response, 404, "Eliminar un TipoMedioPago inexistente debería devolver 404.")

    def test_toggle_activo_tipo_medio_pago(self):
        url = reverse("pagos:toggle_activo", args=[self.tipo_pago.id])
        response = self.client.post(url)
        self.assertStatus(response, 302, "El toggle activo debería redirigir al listado (302).")

    def test_listar_tipos_medio_pago_sin_login(self):
        self.client.logout()
        url = reverse("pagos:listar_tipos_medio_pago")
        response = self.client.get(url)
        self.assertStatus(response, 302, "El listado de tipos de pago debería redirigir al login si no hay sesión (302).")
