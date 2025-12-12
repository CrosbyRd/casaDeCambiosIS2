from datetime import date, timedelta, datetime
from decimal import Decimal
import random
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from monedas.models import Moneda
from transacciones.models import Transaccion
from ganancias.models import RegistroGanancia


MONEDAS_CLAVE = ["ARS"]  # 👈 solo estas


class Command(BaseCommand):
    help = (
        "Genera transacciones simuladas COMPLETADAS para USD, BRL y EUR "
        "desde el 1/9/2025 al 10/12/2025. "
        "Sirve para que en el dashboard se vea mucha actividad en esas monedas, "
        "sin crear demasiados datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-day",
            type=int,
            default=3,
            help=(
                "Cantidad de transacciones por día, por moneda y por tipo "
                "(COMPRA y VENTA). Por defecto: 3."
            ),
        )
        parser.add_argument(
            "--max-total",
            type=int,
            default=240,  # 👈 nunca más de 240 transacciones
            help=(
                "Número máximo de transacciones a crear en total. "
                "Por defecto: 240 (para no superar ~250)."
            ),
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Seed para el generador aleatorio (opcional, para reproducibilidad).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra un resumen de lo que se generaría, pero SIN escribir en la base.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="No pedir confirmación interactiva (útil para scripts).",
        )

    def handle(self, *args, **options):
        per_day = options["per_day"]
        max_total = options["max_total"]
        seed = options["seed"]
        dry_run = options["dry_run"]

        if per_day <= 0:
            self.stderr.write("El parámetro --per-day debe ser >= 1.")
            return
        if max_total is not None and max_total <= 0:
            self.stderr.write("El parámetro --max-total debe ser > 0.")
            return

        if seed is not None:
            random.seed(seed)

        # Moneda base PYG
        try:
            moneda_pyg = Moneda.objects.get(codigo="PYG")
        except Moneda.DoesNotExist:
            self.stderr.write("No se encontró la moneda base PYG en Moneda.")
            return

        # Solo las monedas clave que existan realmente en la tabla
        monedas_obj = list(Moneda.objects.filter(codigo__in=MONEDAS_CLAVE))
        codigos_encontrados = [m.codigo for m in monedas_obj]
        faltantes = [c for c in MONEDAS_CLAVE if c not in codigos_encontrados]

        if faltantes:
            self.stderr.write(
                f"Advertencia: estas monedas clave no existen en Moneda: {', '.join(faltantes)}"
            )

        if not monedas_obj:
            self.stderr.write("No se encontró ninguna de las monedas clave en Moneda.")
            return

        # Usamos una transacción completada como plantilla
        plantilla = Transaccion.objects.filter(estado="completada").first()
        if not plantilla:
            self.stderr.write(
                "No hay ninguna Transaccion 'completada' para usar como plantilla."
            )
            return

        # Rango de fechas: 1 de septiembre a 10 de diciembre de 2025
        start_date = date(2025, 5, 26)
        end_date = date(2025, 5, 27)
        dias_teoricos = (end_date - start_date).days + 1

        # Máximo teórico si se usaran TODOS los días (solo para info)
        total_tx_teorico = dias_teoricos * len(monedas_obj) * 2 * per_day
        total_tx_estimado = min(total_tx_teorico, max_total or total_tx_teorico)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "==> SEMBRAR TRANSACCIONES PARA MONEDAS CLAVE (USD/BRL/EUR) <=="
        ))
        self.stdout.write(f"Rango de fechas: {start_date} al {end_date} (inclusive)")
        self.stdout.write(f"Monedas clave encontradas: {', '.join(codigos_encontrados)}")
        self.stdout.write(f"Transacciones por día/moneda/tipo: {per_day}")
        self.stdout.write(f"Máximo absoluto (--max-total): {max_total}")
        self.stdout.write(
            f"Transacciones TEÓRICAS posibles (sin límite): {total_tx_teorico}"
        )
        self.stdout.write(
            f"Transacciones ESTIMADAS a crear (con límite): {total_tx_estimado}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: no se crearán transacciones ni registros de ganancia."
            ))
            return

        if not options["confirm"]:
            resp = input(
                "\nESTO CREARÁ NUEVAS TRANSACCIONES SOLO PARA DATOS DE PRUEBA.\n"
                "Asegúrate de estar en una base de DESARROLLO.\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        tz = timezone.get_current_timezone()
        creadas = 0
        stop = False

        with transaction.atomic():
            dia_actual = start_date
            while dia_actual <= end_date and not stop:
                for moneda in monedas_obj:
                    if stop:
                        break
                    for tipo in ("venta", "compra"):
                        if stop:
                            break
                        for _ in range(per_day):
                            if max_total is not None and creadas >= max_total:
                                stop = True
                                break

                            # Hora aleatoria entre 9:00 y 17:59
                            hora = random.randint(9, 17)
                            minuto = random.randint(0, 59)
                            segundo = random.randint(0, 59)
                            dt = datetime(
                                dia_actual.year,
                                dia_actual.month,
                                dia_actual.day,
                                hora,
                                minuto,
                                segundo,
                            )
                            dt_aware = timezone.make_aware(dt, tz)

                            nueva = Transaccion()

                            # Copiamos campos de plantilla y luego sobrescribimos lo que nos interese
                            for field in Transaccion._meta.fields:
                                nombre = field.name

                                if field.primary_key:
                                    continue
                                if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                                    continue
                                if nombre in (
                                    "tipo_operacion",
                                    "estado",
                                    "moneda_origen",
                                    "moneda_destino",
                                    "monto_origen",
                                    "monto_destino",
                                ):
                                    continue

                                valor = getattr(plantilla, nombre)

                                # Campos únicos → generamos valor nuevo seguro
                                if getattr(field, "unique", False):
                                    if isinstance(valor, str):
                                        max_len = field.max_length or 255
                                        valor = uuid.uuid4().hex[:max_len]
                                    else:
                                        valor = None

                                setattr(nueva, nombre, valor)

                            base_monto = 800_000  # 1 millón PYG como base
                            variacion = random.randint(-600_000, 600_000)   # ±600k
                            monto_pyg = Decimal(max(600_000, base_monto + variacion))

                            # Tasa a partir de la plantilla con leve variación (±5%)
                            tasa_base = getattr(plantilla, "tasa_cambio_aplicada", Decimal("1.0"))
                            factor_variacion = Decimal(str(random.uniform(0.95, 1.05)))
                            tasa = (Decimal(tasa_base) * factor_variacion).quantize(Decimal("0.0001"))

                            nueva.tipo_operacion = tipo
                            nueva.estado = "completada"

                            if tipo == "venta":
                                # Cliente entrega PYG, recibe moneda extranjera
                                nueva.moneda_origen = moneda_pyg
                                nueva.moneda_destino = moneda
                                nueva.monto_origen = monto_pyg
                                nueva.monto_destino = (monto_pyg / tasa).quantize(Decimal("0.01"))
                            else:  # compra
                                # Cliente entrega moneda extranjera, recibe PYG
                                nueva.moneda_origen = moneda
                                nueva.moneda_destino = moneda_pyg
                                nueva.monto_destino = monto_pyg
                                nueva.monto_origen = (monto_pyg / tasa).quantize(Decimal("0.01"))

                            # Comisiones: basadas en la plantilla con variación suave
                            comision_cot = getattr(plantilla, "comision_cotizacion", Decimal("0.0"))
                            comision_aplicada = getattr(plantilla, "comision_aplicada", Decimal("0.0"))
                            factor_com = Decimal(str(random.uniform(0.3, 0.7)))

                            nueva.comision_cotizacion = (
                                Decimal(comision_cot) * factor_com
                            ).quantize(Decimal("0.01"))
                            nueva.comision_aplicada = (
                                Decimal(comision_aplicada) * factor_com
                            ).quantize(Decimal("0.01"))

                            # Guardamos (dispara signal de ganancias)
                            nueva.save()

                            # Ajustamos timestamps de la transacción
                            Transaccion.objects.filter(pk=nueva.pk).update(
                                fecha_creacion=dt_aware,
                                fecha_actualizacion=dt_aware,
                            )

                            # Ajustamos fecha_registro del RegistroGanancia asociado
                            try:
                                rg = nueva.registro_ganancia
                            except RegistroGanancia.DoesNotExist:
                                rg = None

                            if rg is not None:
                                RegistroGanancia.objects.filter(pk=rg.pk).update(
                                    fecha_registro=dt_aware
                                )

                            creadas += 1

                # En lugar de sumar 1 día, saltamos 5–7 días (promedio ~6)
                step_days = 1
                dia_actual += timedelta(days=step_days)

        self.stdout.write(self.style.SUCCESS(
            f"\nTransacciones simuladas creadas con éxito: {creadas} "
            f"(límite aplicado: max_total={max_total})."
        ))
