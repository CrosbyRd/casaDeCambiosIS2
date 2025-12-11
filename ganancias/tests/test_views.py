# ganancias/tests/tests_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from monedas.models import Moneda
from transacciones.models import Transaccion
from ganancias.models import RegistroGanancia
from clientes.models import Cliente
import uuid

CustomUser = get_user_model()


class DashboardGananciasAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.eur = Moneda.objects.create(codigo="EUR", nombre="Euro")

        self.analyst = CustomUser.objects.create_user(
            email="analyst@test.com", password="12345",
            first_name="Ana", last_name="Lista", is_active=True
        )
        group = Group.objects.create(name="Analista")
        self.analyst.groups.add(group)

        self.staff = CustomUser.objects.create_user(
            email="staff@test.com", password="12345",
            first_name="Staff", last_name="User", is_active=True, is_staff=True
        )

    def test_requires_login(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_access_with_analyst_group(self):
        self.client.force_login(self.analyst)
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_access_with_staff(self):
        self.client.force_login(self.staff)
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_access_denied_without_group_or_staff(self):
        user = CustomUser.objects.create_user(
            email="user@test.com", password="12345",
            first_name="U", last_name="Ser", is_active=True
        )
        self.client.force_login(user)
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)


class DashboardGananciasMetricsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")

        self.user = CustomUser.objects.create_user(
            email="analyst@test.com", password="12345",
            first_name="Ana", last_name="Lista", is_active=True
        )
        Group.objects.create(name="Analista")
        self.user.groups.add(Group.objects.get(name="Analista"))
        self.client.force_login(self.user)

        # Cliente y operador obligatorios
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True,
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )

        # Transacciones con código único
        t1 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10"), monto_destino=Decimal("10"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        t2 = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("20"), monto_destino=Decimal("20"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        # Asegurar fechas diferentes para gráfico
        r1 = RegistroGanancia.objects.get(transaccion=t1)
        r1.fecha_registro = timezone.now() - timezone.timedelta(days=1)
        r1.save()
        r2 = RegistroGanancia.objects.get(transaccion=t2)
        r2.fecha_registro = timezone.now()
        r2.save()

    def test_context_includes_total_periodo(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ganancia_total_periodo", resp.context)

    def test_total_periodo_calculation(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        total = resp.context["ganancia_total_periodo"]
        # t1: (0.10-0)*10 → 1.0 ; t2: (0.05-0.01)*20 → 0.8
        self.assertEqual(total, Decimal("1.8"))

    def test_ganancias_por_dia_list(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertIn("ganancias_por_dia", resp.context)
        self.assertGreaterEqual(resp.context["ganancias_por_dia"].count(), 1)

    def test_fechas_y_totales_grafico(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertTrue(len(resp.context["fechas_grafico"]) >= 1)
        self.assertTrue(len(resp.context["totales_grafico"]) >= 1)

    def test_ganancias_por_moneda_lista_serializable(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        ganancias_por_moneda = resp.context["ganancias_por_moneda"]
        self.assertIsInstance(ganancias_por_moneda, list)
        if ganancias_por_moneda:
            self.assertIn("moneda_operada__codigo", ganancias_por_moneda[0])
            self.assertIn("total_moneda", ganancias_por_moneda[0])

    def test_context_includes_todas_las_monedas(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertIn("todas_las_monedas", resp.context)
        self.assertGreaterEqual(resp.context["todas_las_monedas"].count(), 1)

    def test_context_includes_selected_filters(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url, {"tipo_operacion": "venta"})
        self.assertEqual(resp.context["tipo_operacion_seleccionado"], "venta")


class DashboardGananciasFiltersTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.eur = Moneda.objects.create(codigo="EUR", nombre="Euro")

        self.user = CustomUser.objects.create_user(
            email="analyst@test.com", password="12345",
            first_name="Ana", last_name="Lista", is_active=True
        )
        Group.objects.create(name="Analista")
        self.user.groups.add(Group.objects.get(name="Analista"))
        self.client.force_login(self.user)

        # Cliente y operador obligatorios
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True,
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )

        # Transacciones con código único
        t1 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10"), monto_destino=Decimal("10"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        r1 = RegistroGanancia.objects.get(transaccion=t1)
        r1.fecha_registro = timezone.now() - timezone.timedelta(days=10)
        r1.save()

        t2 = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.eur, moneda_destino=self.eur,
            monto_origen=Decimal("20"), monto_destino=Decimal("20"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.05"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        r2 = RegistroGanancia.objects.get(transaccion=t2)
        r2.fecha_registro = timezone.now() - timezone.timedelta(days=5)
        r2.save()

        t3 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.eur, moneda_destino=self.eur,
            monto_origen=Decimal("30"), monto_destino=Decimal("30"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        r3 = RegistroGanancia.objects.get(transaccion=t3)
        r3.fecha_registro = timezone.now()
        r3.save()

    def test_filter_by_fecha_inicio(self):
        url = reverse("ganancias:dashboard_ganancias")
        start = (timezone.now() - timezone.timedelta(days=7)).date().strftime("%Y-%m-%d")
        resp = self.client.get(url, {"fecha_inicio": start})
        self.assertTrue(all(r["dia"] >= timezone.datetime.strptime(start, "%Y-%m-%d").date()
                            for r in resp.context["ganancias_por_dia"]))

    def test_filter_by_fecha_fin(self):
        url = reverse("ganancias:dashboard_ganancias")
        end = (timezone.now() - timezone.timedelta(days=7)).date().strftime("%Y-%m-%d")
        resp = self.client.get(url, {"fecha_fin": end})
        self.assertTrue(all(r["dia"] <= timezone.datetime.strptime(end, "%Y-%m-%d").date()
                            for r in resp.context["ganancias_por_dia"]))

    def test_filter_by_both_dates(self):
        url = reverse("ganancias:dashboard_ganancias")
        start = (timezone.now() - timezone.timedelta(days=6)).date().strftime("%Y-%m-%d")
        end = (timezone.now() - timezone.timedelta(days=1)).date().strftime("%Y-%m-%d")
        resp = self.client.get(url, {"fecha_inicio": start, "fecha_fin": end})
        for r in resp.context["ganancias_por_dia"]:
            self.assertTrue((r["dia"] >= timezone.datetime.strptime(start, "%Y-%m-%d").date())
                            and (r["dia"] <= timezone.datetime.strptime(end, "%Y-%m-%d").date()))

    def test_filter_by_tipo_operacion_venta(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url, {"tipo_operacion": "venta"})
        for g in resp.context["ganancias_por_dia"]:
            day_regs = RegistroGanancia.objects.filter(fecha_registro__date=g["dia"])
            self.assertTrue(all(r.transaccion.tipo_operacion == "venta" for r in day_regs))

    def test_filter_by_tipo_operacion_compra(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url, {"tipo_operacion": "compra"})
        for g in resp.context["ganancias_por_dia"]:
            day_regs = RegistroGanancia.objects.filter(fecha_registro__date=g["dia"])
            self.assertTrue(all(r.transaccion.tipo_operacion == "compra" for r in day_regs))


    def test_filter_by_moneda_operada(self):
        eur_id = self.eur.id
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url, {"moneda_operada": eur_id})
        ganancias_por_moneda = resp.context["ganancias_por_moneda"]
        if ganancias_por_moneda:
            self.assertTrue(all(item["moneda_operada__codigo"] == "EUR" for item in ganancias_por_moneda))

    def test_total_periodo_with_filters(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp_all = self.client.get(url)
        total_all = resp_all.context["ganancia_total_periodo"]

        resp_venta = self.client.get(url, {"tipo_operacion": "venta"})
        total_venta = resp_venta.context["ganancia_total_periodo"]

        self.assertTrue(total_all >= total_venta)

    def test_orden_por_moneda_desc(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        lista = resp.context["ganancias_por_moneda"]
        if len(lista) >= 2:
            self.assertTrue(lista[0]["total_moneda"] >= lista[1]["total_moneda"])

    def test_template_render(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertTemplateUsed(resp, "ganancias/dashboard_ganancias.html")

    def test_context_includes_selected_params(self):
        url = reverse("ganancias:dashboard_ganancias")
        params = {
            "fecha_inicio": (timezone.now() - timezone.timedelta(days=3)).date().strftime("%Y-%m-%d"),
            "fecha_fin": timezone.now().date().strftime("%Y-%m-%d"),
            "moneda_operada": self.eur.id,
            "tipo_operacion": "venta",
        }
        resp = self.client.get(url, params)
        self.assertEqual(resp.context["fecha_inicio_seleccionada"], params["fecha_inicio"])
        self.assertEqual(resp.context["fecha_fin_seleccionada"], params["fecha_fin"])
        self.assertEqual(resp.context["moneda_operada_seleccionada"], str(params["moneda_operada"]))
        self.assertEqual(resp.context["tipo_operacion_seleccionado"], "venta")

    def test_maneja_ausencia_de_registros(self):
        RegistroGanancia.objects.all().delete()
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertEqual(resp.context["ganancia_total_periodo"], 0)

    def test_grafico_fechas_ordenado(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        fechas = resp.context["fechas_grafico"]
        if len(fechas) >= 2:
            self.assertTrue(fechas == sorted(fechas))

    def test_totales_grafico_son_floats(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        totales = resp.context["totales_grafico"]
        self.assertTrue(all(isinstance(v, float) for v in totales))

    def test_filtros_invalidos_no_rompen(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url, {"tipo_operacion": "invalido"})
        self.assertEqual(resp.status_code, 200)

    def test_moneda_operada_filtro_id_string(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url, {"moneda_operada": str(self.usd.id)})
        self.assertEqual(resp.status_code, 200)

    def test_sin_fechas_muestra_historico(self):
        url = reverse("ganancias:dashboard_ganancias")
        resp = self.client.get(url)
        self.assertIsNone(resp.context["fecha_inicio_seleccionada"])
        self.assertIsNone(resp.context["fecha_fin_seleccionada"])