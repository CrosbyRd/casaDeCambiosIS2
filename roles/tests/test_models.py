# roles/tests/test_models_roles.py
from django.test import TestCase
from django.contrib.auth.models import Permission
from roles.models import Role

class RoleModelTest(TestCase):
    def setUp(self):
        self.permission = Permission.objects.first()
        self.role = Role.objects.create(
            name="Administrador",
            description="Acceso completo al sistema."
        )
        self.role.permissions.add(self.permission)

    def test_role_creation(self):
        self.assertEqual(self.role.name, "Administrador")
        self.assertEqual(self.role.description, "Acceso completo al sistema.")

    def test_role_permissions_assigned(self):
        self.assertIn(self.permission, self.role.permissions.all())

    def test_role_str(self):
        self.assertEqual(str(self.role), "Administrador")

    def test_role_meta_config(self):
        self.assertEqual(Role._meta.verbose_name, "Rol")
        self.assertEqual(Role._meta.verbose_name_plural, "Roles")
