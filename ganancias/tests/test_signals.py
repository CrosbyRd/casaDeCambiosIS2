# ganancias/tests/test_signals.py
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
import uuid

from django.contrib.auth import get_user_model
from monedas.models import Moneda
from transacciones.models import Transaccion
from ganancias.models import RegistroGanancia
from clientes.models import Cliente

CustomUser = get_user_model()


class BaseSignalTest(TestCase):
    def setUp(self):
        self.pyg = Moneda.objects.create(codigo="PYG", nombre="Guaraní")
        self.usd = Moneda.objects.create(codigo="USD", nombre="Dólar")
        self.eur = Moneda.objects.create(codigo="EUR", nombre="Euro")
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            categoria=Cliente.Categoria.MINORISTA,
            activo=True
        )
        self.operador = CustomUser.objects.create_user(
            email="operador@test.com",
            password="12345"
        )


class SignalVentaTests(BaseSignalTest):
    def test_crea_registro_en_venta(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = ((Decimal("0.05") - Decimal("0.01")) * Decimal("80.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)
        self.assertEqual(reg.moneda_ganancia.codigo, "PYG")
        self.assertEqual(reg.moneda_operada.codigo, "USD")
        self.assertIsNotNone(reg.fecha_registro)

    def test_actualiza_registro_si_transaccion_cambia(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("50.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg1 = RegistroGanancia.objects.get(transaccion=tx)
        tx.comision_aplicada = Decimal("0.02")
        tx.monto_destino = Decimal("60.00")
        tx.save()
        reg2 = RegistroGanancia.objects.get(transaccion=tx)
        esperado = ((Decimal("0.05") - Decimal("0.02")) * Decimal("60.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg2.ganancia_registrada, esperado)
        self.assertEqual(reg1.transaccion_id, reg2.transaccion_id)

    def test_no_crea_registro_si_estado_pendiente(self):
        tx = Transaccion.objects.create(
            estado="pendiente", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        self.assertFalse(RegistroGanancia.objects.filter(transaccion=tx).exists())

    def test_crea_registro_al_cambiar_a_completada(self):
        tx = Transaccion.objects.create(
            estado="pendiente", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        tx.estado = "completada"
        tx.save()
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = ((Decimal("0.05") - Decimal("0.01")) * Decimal("80.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_moneda_operada_en_venta_usa_destino(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.eur, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("90.00"),
            comision_cotizacion=Decimal("0.02"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        self.assertEqual(reg.moneda_operada, self.usd)


class SignalCompraTests(BaseSignalTest):
    def test_crea_registro_en_compra(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("120.00"), monto_destino=Decimal("100.00"),
            comision_cotizacion=Decimal("0.03"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = ((Decimal("0.03") - Decimal("0.01")) * Decimal("120.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)
        self.assertEqual(reg.moneda_operada.codigo, "USD")

    def test_moneda_operada_en_compra_usa_origen(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.eur, moneda_destino=self.usd,
            monto_origen=Decimal("120.00"), monto_destino=Decimal("100.00"),
            comision_cotizacion=Decimal("0.03"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        self.assertEqual(reg.moneda_operada, self.eur)


class SignalTipoOperacionTests(BaseSignalTest):
    def test_no_crea_registro_si_tipo_operacion_desconocido(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="arbitraje",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("50.00"), monto_destino=Decimal("50.00"),
            comision_cotizacion=Decimal("0.02"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        self.assertFalse(RegistroGanancia.objects.filter(transaccion=tx).exists())


class SignalMonedaPYGTests(BaseSignalTest):
    def test_no_crea_registro_si_no_existe_pyg(self):
        self.pyg.delete()
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        self.assertFalse(RegistroGanancia.objects.filter(transaccion=tx).exists())


class SignalGananciaPrecisionTests(BaseSignalTest):
    def test_ganancia_cero_si_comisiones_iguales(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.01"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = Decimal("0.00").quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_ganancia_grande_valida(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("999999999999.99"), monto_destino=Decimal("999999999999.99"),
            comision_cotizacion=Decimal("0.02"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = (Decimal("0.02") * Decimal("999999999999.99")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_ganancia_acepta_dos_decimales(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10.00"), monto_destino=Decimal("1.23"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = (Decimal("0.10") * Decimal("1.23")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_ganancia_con_monto_destino_cero_en_venta(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("0.00"), monto_destino=Decimal("0.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = Decimal("0.00").quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_ganancia_con_monto_origen_cero_en_compra(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("0.00"), monto_destino=Decimal("0.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = Decimal("0.00").quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_montos_con_muchos_decimales_se_mantienen_precisos(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("1.2345"), monto_destino=Decimal("1.2345"),
            comision_cotizacion=Decimal("0.1234"), comision_aplicada=Decimal("0.0234"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = ((Decimal("0.1234") - Decimal("0.0234")) * Decimal("1.2345")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)


class SignalFechaRegistroTests(BaseSignalTest):
    def test_fecha_registro_se_setea(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.05"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        self.assertIsNotNone(reg.fecha_registro)

    def test_fecha_registro_se_actualiza_en_update(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("120.00"), monto_destino=Decimal("100.00"),
            comision_cotizacion=Decimal("0.03"), comision_aplicada=Decimal("0.01"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg1 = RegistroGanancia.objects.get(transaccion=tx)
        # Pequeña espera simulada con una nueva fecha al guardar
        tx.comision_aplicada = Decimal("0.00")
        tx.save()
        reg2 = RegistroGanancia.objects.get(transaccion=tx)
        self.assertGreaterEqual(reg2.fecha_registro, reg1.fecha_registro)


class SignalUpdateOrCreateTests(BaseSignalTest):
    def test_update_or_create_evita_pk_duplicada(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("200.00"), monto_destino=Decimal("150.00"),
            comision_cotizacion=Decimal("0.02"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg1 = RegistroGanancia.objects.get(transaccion=tx)
        tx.monto_destino = Decimal("160.00")
        tx.save()
        reg2 = RegistroGanancia.objects.get(transaccion=tx)
        self.assertEqual(reg1.transaccion_id, reg2.transaccion_id)
        self.assertEqual(RegistroGanancia.objects.count(), 1)

    def test_filtrado_por_moneda_ganancia(self):
        t1 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10.00"), monto_destino=Decimal("9.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        t2 = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("12.00"), monto_destino=Decimal("10.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        qs = RegistroGanancia.objects.filter(moneda_ganancia__codigo="PYG")
        self.assertEqual(qs.count(), 2)

    def test_filtrado_por_moneda_operada(self):
        # venta usa destino (USD), compra usa origen (EUR) para que haya 1 y 1
        t1 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.eur, moneda_destino=self.usd,
            monto_origen=Decimal("10.00"), monto_destino=Decimal("9.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        t2 = Transaccion.objects.create(
            estado="completada", tipo_operacion="compra",
            moneda_origen=self.eur, moneda_destino=self.usd,
            monto_origen=Decimal("12.00"), monto_destino=Decimal("10.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        qs_usd = RegistroGanancia.objects.filter(moneda_operada__codigo="USD")
        qs_eur = RegistroGanancia.objects.filter(moneda_operada__codigo="EUR")
        self.assertEqual(qs_usd.count(), 1)
        self.assertEqual(qs_eur.count(), 1)

    def test_ordering_por_fecha_desc(self):
        t1 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10.00"), monto_destino=Decimal("10.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        t2 = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("20.00"), monto_destino=Decimal("20.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        r1 = RegistroGanancia.objects.get(transaccion=t1)
        r2 = RegistroGanancia.objects.get(transaccion=t2)
        registros = list(RegistroGanancia.objects.all())
        self.assertEqual(registros[0], r2)
        self.assertEqual(registros[1], r1)


class SignalRobustezTests(BaseSignalTest):
    def test_comision_aplicada_mayor_a_cotizacion_da_ganancia_negativa(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("100.00"), monto_destino=Decimal("80.00"),
            comision_cotizacion=Decimal("0.01"), comision_aplicada=Decimal("0.02"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        reg = RegistroGanancia.objects.get(transaccion=tx)
        esperado = ((Decimal("0.01") - Decimal("0.02")) * Decimal("80.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg.ganancia_registrada, esperado)

    def test_no_registro_si_estado_bloqueada(self):
        tx = Transaccion.objects.create(
            estado="bloqueada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10.00"), monto_destino=Decimal("10.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        self.assertFalse(RegistroGanancia.objects.filter(transaccion=tx).exists())

    def test_registro_se_recalcula_en_multiples_updates(self):
        tx = Transaccion.objects.create(
            estado="completada", tipo_operacion="venta",
            moneda_origen=self.usd, moneda_destino=self.usd,
            monto_origen=Decimal("10.00"), monto_destino=Decimal("10.00"),
            comision_cotizacion=Decimal("0.10"), comision_aplicada=Decimal("0.00"),
            tasa_cambio_aplicada=Decimal("7300.00"),
            cliente=self.cliente, usuario_operador=self.operador, codigo_operacion_tauser=str(uuid.uuid4())[:10],
        )
        tx.comision_aplicada = Decimal("0.02")
        tx.save()
        reg1 = RegistroGanancia.objects.get(transaccion=tx)
        esperado1 = ((Decimal("0.10") - Decimal("0.02")) * Decimal("10.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg1.ganancia_registrada, esperado1)
        tx.comision_cotizacion = Decimal("0.20")
        tx.save()
        reg2 = RegistroGanancia.objects.get(transaccion=tx)
        esperado2 = ((Decimal("0.20") - Decimal("0.02")) * Decimal("10.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg2.ganancia_registrada, esperado2)
        tx.monto_destino = Decimal("5.00")
        tx.save()
        reg3 = RegistroGanancia.objects.get(transaccion=tx)
        esperado3 = ((Decimal("0.20") - Decimal("0.02")) * Decimal("5.00")).quantize(Decimal("0.00"))
        self.assertEqual(reg3.ganancia_registrada, esperado3)
