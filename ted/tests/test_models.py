from django.test import TestCase
from ted.models import TedPerms, TedTerminal

class TedPermsModelTests(TestCase):
    def test_permissions_exist(self):
        perms = [p[0] for p in TedPerms._meta.permissions]
        self.assertIn('puede_operar_terminal', perms)
        self.assertIn('puede_gestionar_inventario', perms)

class TedTerminalModelTests(TestCase):
    def test_create_terminal(self):
        t = TedTerminal.objects.create(serial='TED-001', direccion='Sucursal Central')
        self.assertEqual(str(t), 'TED-001')

    def test_unique_serial(self):
        TedTerminal.objects.create(serial='TED-002')
        with self.assertRaises(Exception):
            TedTerminal.objects.create(serial='TED-002')
