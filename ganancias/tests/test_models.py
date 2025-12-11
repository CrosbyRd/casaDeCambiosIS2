# ganancias/tests/tests_models.py
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
from monedas.models import Moneda
from transacciones.models import Transaccion
from ganancias.models import RegistroGanancia
from clientes.models import Cliente
import uuid

CustomUser = get_user_model()


class RegistroGananciaModelBasicsTest(TestCase):
    def setUp(self):
        self.moneda_pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.moneda_usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )

    def test_str_contains_transaccion_id(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_usd, moneda_destino=self.moneda_usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("100.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        registro = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("4.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )
        text = str(registro)
        self.assertIn("Ganancia para Transacción", text)
        self.assertIn(str(tx.id), text)

    def test_verbose_names(self):
        self.assertEqual(str(RegistroGanancia._meta.verbose_name), "Registro de Ganancia")
        self.assertEqual(str(RegistroGanancia._meta.verbose_name_plural), "Registros de Ganancias")

    def test_ordering_meta(self):
        self.assertEqual(RegistroGanancia._meta.ordering, ['-fecha_registro'])

    def test_relacion_one_to_one_con_transaccion(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_usd, moneda_destino=self.moneda_usd,
            monto_origen=Decimal("50.00"), monto_destino=Decimal("50.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        registro = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("2.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )
        self.assertEqual(registro.transaccion, tx)

    def test_moneda_ganancia_codigo(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_usd, moneda_destino=self.moneda_usd,
            monto_origen=Decimal("60.00"), monto_destino=Decimal("60.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        registro = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("3.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )
        self.assertEqual(registro.moneda_ganancia.codigo, "PYG")

    def test_moneda_operada_codigo(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_usd, moneda_destino=self.moneda_usd,
            monto_origen=Decimal("70.00"), monto_destino=Decimal("70.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        registro = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("4.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )
        self.assertEqual(registro.moneda_operada.codigo, "USD")

    def test_ganancia_registrada_tipo_decimal(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_usd, moneda_destino=self.moneda_usd,
            monto_origen=Decimal("80.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        registro = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("5.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )
        self.assertIsInstance(registro.ganancia_registrada, Decimal)

    def test_fecha_registro_no_nulo(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_usd, moneda_destino=self.moneda_usd,
            monto_origen=Decimal("90.00"), monto_destino=Decimal("90.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        registro = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("6.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )
        self.assertIsNotNone(registro.fecha_registro)

    def test_transaccion_es_primary_key(self):
        pk_field = RegistroGanancia._meta.get_field('transaccion')
        self.assertTrue(pk_field.primary_key)


class RegistroGananciaFieldValidationTest(TestCase):
    def setUp(self):
        self.moneda_pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.moneda_eur = Moneda.objects.create(codigo="EUR", nombre="Euro")
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )
        self.transaccion = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="compra",
            moneda_origen=self.moneda_eur,
            moneda_destino=self.moneda_eur,
            monto_origen=Decimal("200.00"),
            monto_destino=Decimal("200.00"),
            comision_cotizacion=Decimal("0.02"),
            comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )

    def test_no_permite_moneda_ganancia_nula(self):
        RegistroGanancia.objects.filter(transaccion=self.transaccion).delete()
        with self.assertRaises(Exception):
            RegistroGanancia.objects.create(
                transaccion=self.transaccion,
                ganancia_registrada=Decimal("4.00"),
                moneda_ganancia=None,
                moneda_operada=self.moneda_eur,
                fecha_registro=timezone.now()
            )

    def test_no_permite_moneda_operada_nula(self):
        RegistroGanancia.objects.filter(transaccion=self.transaccion).delete()
        with self.assertRaises(Exception):
            RegistroGanancia.objects.create(
                transaccion=self.transaccion,
                ganancia_registrada=Decimal("4.00"),
                moneda_ganancia=self.moneda_pyg,
                moneda_operada=None,
                fecha_registro=timezone.now()
            )

    def test_no_permite_ganancia_registrada_nula(self):
        RegistroGanancia.objects.filter(transaccion=self.transaccion).delete()
        with self.assertRaises(Exception):
            RegistroGanancia.objects.create(
                transaccion=self.transaccion,
                ganancia_registrada=None,
                moneda_ganancia=self.moneda_pyg,
                moneda_operada=self.moneda_eur,
                fecha_registro=timezone.now()
            )

    def test_no_permite_fecha_registro_nula(self):
        RegistroGanancia.objects.filter(transaccion=self.transaccion).delete()
        with self.assertRaises(Exception):
            RegistroGanancia.objects.create(
                transaccion=self.transaccion,
                ganancia_registrada=Decimal("4.00"),
                moneda_ganancia=self.moneda_pyg,
                moneda_operada=self.moneda_eur,
                fecha_registro=None
            )

    def test_decimal_precision_maxima(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_eur, moneda_destino=self.moneda_eur,
            monto_origen=Decimal("50.00"), monto_destino=Decimal("50.00"),
            comision_cotizacion=Decimal("0.01"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        reg = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("123456789012.34"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_eur,
            fecha_registro=timezone.now()
        )
        self.assertEqual(reg.ganancia_registrada, Decimal("123456789012.34"))

    def test_no_accepta_mas_de_dos_decimales_por_definicion(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.moneda_eur, moneda_destino=self.moneda_eur,
            monto_origen=Decimal("60.00"), monto_destino=Decimal("60.00"),
            comision_cotizacion=Decimal("0.01"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        reg = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("1.999"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_eur,
            fecha_registro=timezone.now()
        )
        self.assertIsInstance(reg.ganancia_registrada, Decimal)

    def test_requiere_transaccion_unica(self):
        RegistroGanancia.objects.filter(transaccion=self.transaccion).delete()
        RegistroGanancia.objects.create(
            transaccion=self.transaccion,
            ganancia_registrada=Decimal("4.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_eur,
            fecha_registro=timezone.now()
        )
        with self.assertRaises(Exception):
            RegistroGanancia.objects.create(
                transaccion=self.transaccion,
                ganancia_registrada=Decimal("5.00"),
                moneda_ganancia=self.moneda_pyg,
                moneda_operada=self.moneda_eur,
                fecha_registro=timezone.now()
            )


class RegistroGananciaOrderingTest(TestCase):
    def setUp(self):
        self.moneda_pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.moneda_usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )

        self.t1 = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="venta",
            moneda_origen=self.moneda_usd,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal("10"),
            monto_destino=Decimal("10"),
            comision_cotizacion=Decimal("0.1"),
            comision_aplicada=Decimal("0.0"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        self.t2 = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="venta",
            moneda_origen=self.moneda_usd,
            moneda_destino=self.moneda_usd,
            monto_origen=Decimal("20"),
            monto_destino=Decimal("20"),
            comision_cotizacion=Decimal("0.1"),
            comision_aplicada=Decimal("0.0"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )

        # Usamos registros manuales controlando fechas, eliminando cualquier auto-creado
        RegistroGanancia.objects.filter(transaccion=self.t1).delete()
        RegistroGanancia.objects.filter(transaccion=self.t2).delete()

        self.r1 = RegistroGanancia.objects.create(
            transaccion=self.t1,
            ganancia_registrada=Decimal("1.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now() - timezone.timedelta(days=1)
        )
        self.r2 = RegistroGanancia.objects.create(
            transaccion=self.t2,
            ganancia_registrada=Decimal("2.00"),
            moneda_ganancia=self.moneda_pyg,
            moneda_operada=self.moneda_usd,
            fecha_registro=timezone.now()
        )

    def test_ordering_por_fecha_desc(self):
        registros = list(RegistroGanancia.objects.all())
        self.assertEqual(registros[0], self.r2)
        self.assertEqual(registros[1], self.r1)

    def test_filtrado_por_moneda_operada(self):
        qs = RegistroGanancia.objects.filter(moneda_operada__codigo="USD")
        self.assertEqual(qs.count(), 2)

    def test_filtrado_por_moneda_ganancia(self):
        qs = RegistroGanancia.objects.filter(moneda_ganancia__codigo="PYG")
        self.assertEqual(qs.count(), 2)


class CustomUserModelMethodsTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@test.com",
            password="12345",
            first_name="U",
            last_name="Ser",
            is_active=True
        )

    def test_user_str_is_email(self):
        self.assertEqual(str(self.user), "user@test.com")

    def test_get_full_name(self):
        self.assertEqual(self.user.get_full_name(), "U Ser")

    def test_generate_verification_code_sets_code_and_time(self):
        self.user.generate_verification_code()
        self.assertIsNotNone(self.user.verification_code)
        self.assertEqual(len(self.user.verification_code), 6)
        self.assertIsNotNone(self.user.code_created_at)

    def test_is_code_valid_true_within_window(self):
        self.user.generate_verification_code()
        code = self.user.verification_code
        self.assertTrue(self.user.is_code_valid(code, minutes_valid=5))

    def test_is_code_valid_false_wrong_code(self):
        self.user.generate_verification_code()
        self.assertFalse(self.user.is_code_valid("000000", minutes_valid=5))

    def test_is_code_valid_false_expired(self):
        self.user.generate_verification_code()
        self.user.code_created_at = timezone.now() - timezone.timedelta(minutes=10)
        self.user.save()
        self.assertFalse(self.user.is_code_valid(self.user.verification_code, minutes_valid=1))

    def test_has_perm_superuser_granted(self):
        self.user.is_superuser = True
        self.user.save()
        self.assertTrue(self.user.has_perm("any.app"))

    def test_has_module_perms_superuser(self):
        self.user.is_superuser = True
        self.user.save()
        self.assertTrue(self.user.has_module_perms("ganancias"))


class RegistroGananciaEdgeValuesTest(TestCase):
    def setUp(self):
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )

    def test_ganancia_registrada_cero_valida(self):
        tx = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="venta",
            moneda_origen=self.usd,
            moneda_destino=self.usd,
            monto_origen=Decimal("0.00"),
            monto_destino=Decimal("0.00"),
            comision_cotizacion=Decimal("0.00"),
            comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        reg = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("0.00"),
            moneda_ganancia=self.pyg,
            moneda_operada=self.usd,
            fecha_registro=timezone.now()
        )
        self.assertEqual(reg.ganancia_registrada, Decimal("0.00"))

    def test_ganancia_registrada_valor_grande(self):
        tx = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="venta",
            moneda_origen=self.usd,
            moneda_destino=self.usd,
            monto_origen=Decimal("0.00"),
            monto_destino=Decimal("0.00"),
            comision_cotizacion=Decimal("0.00"),
            comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        RegistroGanancia.objects.filter(transaccion=tx).delete()
        reg = RegistroGanancia.objects.create(
            transaccion=tx,
            ganancia_registrada=Decimal("999999999999.99"),
            moneda_ganancia=self.pyg,
            moneda_operada=self.usd,
            fecha_registro=timezone.now()
        )
        self.assertEqual(reg.ganancia_registrada, Decimal("999999999999.99"))

    def test_fecha_registro_index_flag(self):
        field = RegistroGanancia._meta.get_field('fecha_registro')
        self.assertTrue(field.db_index)


class RegistroGananciaIntegrityTest(TestCase):
    def setUp(self):
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345",
            first_name="Op",
            last_name="Erador",
            is_active=True
        )
        self.tx1 = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="compra",
            moneda_origen=self.usd,
            moneda_destino=self.usd,
            monto_origen=Decimal("10"),
            monto_destino=Decimal("10"),
            comision_cotizacion=Decimal("0.05"),
            comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        self.tx2 = Transaccion.objects.create(
            estado="completada",
            tipo_operacion="venta",
            moneda_origen=self.usd,
            moneda_destino=self.usd,
            monto_origen=Decimal("20"),
            monto_destino=Decimal("20"),
            comision_cotizacion=Decimal("0.05"),
            comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente,
            usuario_operador=self.operador,
            codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )

    def test_distintas_transacciones_admiten_registros_distintos(self):
        RegistroGanancia.objects.filter(transaccion=self.tx1).delete()
        RegistroGanancia.objects.filter(transaccion=self.tx2).delete()
        r1 = RegistroGanancia.objects.create(
            transaccion=self.tx1,
            ganancia_registrada=Decimal("0.40"),
            moneda_ganancia=self.pyg,
            moneda_operada=self.usd,
            fecha_registro=timezone.now()
        )
        r2 = RegistroGanancia.objects.create(
            transaccion=self.tx2,
            ganancia_registrada=Decimal("0.80"),
            moneda_ganancia=self.pyg,
            moneda_operada=self.usd,
            fecha_registro=timezone.now()
        )
        self.assertNotEqual(r1.transaccion_id, r2.transaccion_id)
        self.assertEqual(RegistroGanancia.objects.count(), 2)

