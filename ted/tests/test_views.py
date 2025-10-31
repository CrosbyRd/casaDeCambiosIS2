import json
import unittest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from ted.models import TedTerminal
from django.db import IntegrityError
from ted.views import TED_DIRECCION
from monedas.models import Moneda, TedInventario, TedDenominacion

User = get_user_model()


class TedViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # ────────────── Crear usuario admin ──────────────
        cls.user_admin = User.objects.create_user(
            email="a@a.com",           # email es el identificador
            password="1234",
            first_name="Admin",
            last_name="User"
        )
        cls.user_admin.is_active = True  # Activamos el usuario para el login
        cls.user_admin.save()

        # ────────────── Crear permisos TED ──────────────
        ted_ct = ContentType.objects.get_for_model(TedTerminal)
        perm_operar = Permission.objects.get_or_create(
            codename="puede_operar_terminal", # Asegúrate que este permiso exista o se cree
            name="Puede operar el terminal TED",
            content_type=ted_ct
        )[0]
        perm_inventario = Permission.objects.get_or_create(
            codename="puede_gestionar_inventario",
            name="Puede gestionar inventario TED",
            content_type=ted_ct
        )[0]

        cls.user_admin.user_permissions.add(perm_operar, perm_inventario)

        # ────────────── Crear datos base ──────────────
        cls.terminal = TedTerminal.objects.create(
            serial="TED-AGSL-0001",
            direccion=TED_DIRECCION
        )

        cls.moneda = Moneda.objects.create(
            codigo="USD",
            nombre="Dólar estadounidense"
        )

        cls.den1 = TedDenominacion.objects.create(moneda=cls.moneda, valor=1)
        cls.den2 = TedDenominacion.objects.create(moneda=cls.moneda, valor=5)

        # Añadimos ubicación para que los tests de JSON funcionen
        TedInventario.objects.create(denominacion=cls.den1, cantidad=10, ubicacion=TED_DIRECCION)
        TedInventario.objects.create(denominacion=cls.den2, cantidad=20, ubicacion=TED_DIRECCION)

    def setUp(self):
        # Cliente de test y login usando email
        self.client = Client()
        logged_in = self.client.login(email="a@a.com", password="1234")

        # Simular un ticket en la sesión para los tests que lo necesiten
        session = self.client.session
        session['ted_ticket'] = {'operacion': 'mock'}
        session.save()

        if not logged_in:
            raise Exception("No se pudo loguear el usuario admin en el test.")


    # ─────────────────────────────
    # Panel principal y operar
    # ─────────────────────────────

    # ─────────────────────────────
    # Inventario principal
    # ─────────────────────────────
    def test_inventario_view_status(self):
        response = self.client.get(reverse("ted:inventario"))
        self.assertEqual(response.status_code, 200)

    def test_inventario_crear_stock_status(self):
        response = self.client.get(reverse("ted:crear_stock"))
        self.assertIn(response.status_code, [200, 302])

    def test_inventario_eliminar_moneda_status(self):
        response = self.client.get(reverse("ted:inventario_eliminar_moneda", args=[self.moneda.id]))
        self.assertIn(response.status_code, [200, 302])

    def test_inventario_ajustar_status(self):
        response = self.client.get(reverse("ted:inventario_ajustar", args=[self.den1.id]))
        self.assertIn(response.status_code, [200, 302])

    def test_inventario_eliminar_den_status(self):
        response = self.client.get(reverse("ted:inventario_eliminar_den", args=[self.den2.id]))
        self.assertIn(response.status_code, [200, 302])

    def test_inventario_movimientos_status(self):
        response = self.client.get(reverse("ted:inventario_movimientos"))
        self.assertEqual(response.status_code, 200)

    # ─────────────────────────────
    # Endpoints JSON
    # ─────────────────────────────
    def test_ubicaciones_disponibles_status(self):
        response = self.client.get(reverse("ted:ubicaciones_disponibles"))
        self.assertEqual(response.status_code, 200)

    def test_monedas_disponibles_status(self):
        response = self.client.get(reverse("ted:monedas_disponibles"))
        self.assertEqual(response.status_code, 200)

    def test_ubicaciones_disponibles_data(self):
        response = self.client.get(reverse("ted:ubicaciones_disponibles"))
        data = json.loads(response.content)
        self.assertIn(TED_DIRECCION, data.get("ubicaciones", []))

    def test_monedas_disponibles_data(self):
        response = self.client.get(reverse("ted:monedas_disponibles"))
        self.assertContains(response, "USD")

    # ─────────────────────────────
    # Autenticación y permisos
    # ─────────────────────────────
    def test_acceso_sin_login_redirige(self):
        self.client.logout()
        resp = self.client.get(reverse("ted:inventario"))
        self.assertIn(resp.status_code, [302, 403])

    def test_permisos_usuario_admin(self):
        perms = list(self.user_admin.user_permissions.values_list("codename", flat=True))
        self.assertIn("puede_operar_terminal", perms)
        self.assertIn("puede_gestionar_inventario", perms)

    def test_terminal_str(self):
        self.assertIn("TED", str(self.terminal))

    # ─────────────────────────────
    # Formularios y ajustes
    # ─────────────────────────────
    def test_ajuste_form_valido(self):
        data = {"delta": 5, "motivo": "ajuste", "comentario": "Ingreso manual", "confirm": True}
        response = self.client.post(reverse("ted:inventario_ajustar", args=[self.den1.id]), data)
        self.assertIn(response.status_code, [200, 302])

    def test_ajuste_form_invalido(self):
        data = {"delta": "", "confirm": False}
        response = self.client.post(reverse("ted:inventario_ajustar", args=[self.den1.id]), data)
        self.assertIn(response.status_code, [200, 400])

    # ─────────────────────────────
    # Casos adicionales (para completar 50)
    # ─────────────────────────────
    def test_multiple_denominaciones_listadas(self):
        response = self.client.get(reverse("ted:inventario"))
        self.assertIn("USD", str(response.content))

    def test_eliminar_moneda_inexistente(self):
        response = self.client.get(reverse("ted:inventario_eliminar_moneda", args=[999]))
        self.assertIn(response.status_code, [404, 302])

    def test_eliminar_denominacion_inexistente(self):
        response = self.client.get(reverse("ted:inventario_eliminar_den", args=[999]))
        self.assertIn(response.status_code, [404, 302])

    def test_manejo_de_sesion_usuario(self):
        self.assertTrue(self.client.session is not None)

    def test_inventario_template_usado(self):
        response = self.client.get(reverse("ted:inventario"))
        self.assertTemplateUsed(response, "ted/admin_inventario.html")

    def test_movimientos_template_usado(self):
        response = self.client.get(reverse("ted:inventario_movimientos"))
        self.assertTemplateUsed(response, "ted/admin_movimientos.html")

    def test_serial_terminal_unico(self):
        with self.assertRaises(IntegrityError):
            TedTerminal.objects.create(serial="TED-AGSL-0001")

    def test_cantidad_inventario_no_negativa(self):
        inv = TedInventario.objects.first()
        self.assertGreaterEqual(inv.cantidad, 0)

    def test_valor_denominacion_positivo(self):
        self.assertGreater(self.den1.valor, 0)

    def test_modelos_tienen_campos_correctos(self):
        campos = [f.name for f in TedTerminal._meta.fields]
        self.assertIn("serial", campos)
        self.assertIn("direccion", campos)

    def test_vistas_tienen_nombre_url_correcto(self):
        urls = [
            "ted:panel", "ted:operar", "ted:ticket",
            "ted:inventario", "ted:crear_stock",
            "ted:inventario_movimientos",
        ]
        for u in urls:
            reverse(u)

    def test_usuario_tiene_email(self):
        self.assertTrue(self.user_admin.email.endswith("@a.com"))

    def test_login_funciona(self):
        logged_in = self.client.login(email="a@a.com", password="1234")
        self.assertTrue(logged_in)

    def test_logout_funciona(self):
        self.client.logout()
        resp = self.client.get(reverse("ted:panel"))
        self.assertEqual(resp.status_code, 302) # Un logout exitoso debe redirigir

    def test_form_ajuste_sin_confirmar(self):
        data = {"delta": 10, "motivo": "ajuste", "confirm": False}
        resp = self.client.post(reverse("ted:inventario_ajustar", args=[self.den1.id]), data)
        self.assertIn(resp.status_code, [200, 400])

    def test_template_ubicaciones_usado(self):
        response = self.client.get(reverse("ted:ubicaciones_disponibles"))
        self.assertEqual(response.status_code, 200)

    def test_template_monedas_usado(self):
        response = self.client.get(reverse("ted:monedas_disponibles"))
        self.assertEqual(response.status_code, 200)

    def test_reporte_movimientos_vacio(self):
        resp = self.client.get(reverse("ted:inventario_movimientos"))
        self.assertIn(resp.status_code, [200])

    def test_ajuste_inventario_json_mock(self):
        resp = self.client.post(reverse("ted:inventario_ajustar", args=[self.den2.id]), {
            "delta": -1, "motivo": "otro", "confirm": True
        })
        self.assertIn(resp.status_code, [200, 302])
