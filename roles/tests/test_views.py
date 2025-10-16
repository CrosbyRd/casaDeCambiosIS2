# roles/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Permission
from roles.models import Role
from usuarios.models import CustomUser

HTTP_STATUS_TEXT = {
    200: "Página cargada correctamente (con formulario y/o errores)",
    302: "Redirección a otra página (normalmente éxito de creación/edición/eliminación)",
    403: "Acceso prohibido (usuario sin permisos)",
    404: "Página o recurso no encontrado",
    400: "Solicitud inválida (Bad Request, datos incorrectos en formulario)",
    500: "Error interno del servidor"
}

class RoleViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Crear usuario admin de prueba
        self.admin_user = CustomUser.objects.create_user(
            email="admin@example.com",
            password="12345",
            first_name="Admin",
            last_name="User",
            is_active=True,
        )

        # Crear usuario normal
        self.normal_user = CustomUser.objects.create_user(
            email="user@example.com",
            password="12345",
            first_name="Normal",
            last_name="User",
            is_active=True,
        )

        # Crear permisos
        perm_roles_panel = Permission.objects.get(codename="access_roles_panel")
        perm_user_mgmt = Permission.objects.get(codename="access_user_client_management")

        # Crear rol de prueba con permisos
        self.role_admin_test = Role.objects.create(name="Rol Admin Test")
        self.role_admin_test.permissions.set([perm_roles_panel, perm_user_mgmt])
        self.role_admin_test.save()

        # Asignar rol al admin
        self.admin_user.roles.add(self.role_admin_test)
        self.admin_user.save()

        # Crear roles adicionales para pruebas
        self.role_admin = Role.objects.create(name="Administrador", description="Acceso completo")
        self.role_user = Role.objects.create(name="Usuario", description="Acceso limitado")

    def assertStatus(self, response, expected_status, msg=""):
        message = msg or f"Status recibido: {response.status_code} ({HTTP_STATUS_TEXT.get(response.status_code, 'Desconocido')}), se esperaba {expected_status}."
        self.assertEqual(response.status_code, expected_status, message)

    # --- Tests ---
    def test_role_panel_access_with_login(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("roles:role-panel"))
        self.assertStatus(response, 200)

    def test_role_panel_access_without_login(self):
        response = self.client.get(reverse("roles:role-panel"))
        self.assertStatus(response, 302)

    def test_role_panel_shows_roles(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("roles:role-panel"))
        self.assertStatus(response, 200)
        self.assertIn("usuarios", response.context)

    def test_manage_user_roles_post_assign(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("roles:manage-user-roles", kwargs={"user_id": self.normal_user.id}),
            {"roles": [self.role_admin.id]}
        )
        self.assertStatus(response, 302)
        self.normal_user.refresh_from_db()
        self.assertIn(self.role_admin, self.normal_user.roles.all())

    def test_manage_user_roles_post_clear(self):
        self.normal_user.roles.add(self.role_admin)
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("roles:manage-user-roles", kwargs={"user_id": self.normal_user.id}),
            {"roles": []}
        )
        self.assertStatus(response, 302)
        self.normal_user.refresh_from_db()
        self.assertEqual(self.normal_user.roles.count(), 0)

    def test_manage_user_roles_not_found(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("roles:manage-user-roles", kwargs={"user_id": 999}))
        self.assertStatus(response, 404)
