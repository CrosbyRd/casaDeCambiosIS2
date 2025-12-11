# ganancias/management/commands/redistribuir_valores_ganancias.py

from decimal import Decimal, ROUND_HALF_UP
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ganancias.models import RegistroGanancia


class Command(BaseCommand):
    help = (
        "Redistribuye los valores de ganancia_registrada de forma más uniforme, "
        "agregando variación aleatoria para que no parezcan valores clonados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-factor",
            type=float,
            default=0.6,
            help=(
                "Factor mínimo respecto al promedio. "
                "Ej: 0.6 significa que algunas ganancias pueden ser 60%% del promedio."
            ),
        )
        parser.add_argument(
            "--max-factor",
            type=float,
            default=1.4,
            help=(
                "Factor máximo respecto al promedio. "
                "Ej: 1.4 significa que algunas ganancias pueden ser 140%% del promedio."
            ),
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Seed para el generador aleatorio (para reproducir resultados).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué se haría, pero SIN modificar la base.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="No pedir confirmación interactiva (útil para scripts).",
        )

    def handle(self, *args, **options):
        min_factor = options["min_factor"]
        max_factor = options["max_factor"]
        seed = options["seed"]
        dry_run = options["dry_run"]

        if min_factor <= 0 or max_factor <= 0:
            raise CommandError("min-factor y max-factor deben ser positivos.")

        if min_factor >= max_factor:
            raise CommandError("min-factor debe ser menor que max-factor.")

        if seed is not None:
            random.seed(seed)

        registros = list(RegistroGanancia.objects.order_by("fecha_registro"))
        total_registros = len(registros)

        if total_registros == 0:
            self.stdout.write(self.style.WARNING("No hay RegistroGanancia para modificar."))
            return

        # Total real actual de ganancias
        total_actual = sum((r.ganancia_registrada for r in registros), Decimal("0.00"))
        promedio = (total_actual / Decimal(total_registros)).quantize(Decimal("0.01"))

        self.stdout.write(f"Registros encontrados: {total_registros}")
        self.stdout.write(f"Total actual de ganancias: {total_actual}")
        self.stdout.write(f"Promedio teórico por registro: {promedio}")

        # 1) Generar factores aleatorios alrededor del promedio
        factores = [
            Decimal(str(random.triangular(min_factor, max_factor, 1.0)))
            for _ in range(total_registros)
        ]

        # 2) Calcular valores provisionales
        provisionales = [ (promedio * f) for f in factores ]
        suma_prov = sum(provisionales, Decimal("0.00"))

        if suma_prov == 0:
            raise CommandError("La suma provisional resultó cero, algo anda mal con los factores.")

        # 3) Reescalar para que la suma final coincida con el total_actual
        factor_correccion = (total_actual / suma_prov)
        self.stdout.write(f"Factor de corrección global: {factor_correccion}")

        valores_nuevos = []
        for i, v in enumerate(provisionales):
            nuevo = (v * factor_correccion).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # Evitar que haya valores exactamente iguales demasiadas veces:
            # le sumamos una pequeña variación de centavos según el índice.
            jitter = Decimal(i % 7) * Decimal("0.01")  # entre 0.00 y 0.06
            nuevo = (nuevo + jitter).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if nuevo < Decimal("0.01"):
                nuevo = Decimal("0.01")
            valores_nuevos.append(nuevo)

        # 4) Ajustar el último registro para corregir diferencias por redondeo
        suma_nueva = sum(valores_nuevos, Decimal("0.00"))
        diferencia = (total_actual - suma_nueva).quantize(Decimal("0.01"))

        self.stdout.write(f"Suma nueva antes de corrección: {suma_nueva}")
        self.stdout.write(f"Diferencia respecto al total original: {diferencia}")

        valores_nuevos[-1] = (valores_nuevos[-1] + diferencia).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 5) Preview
        self.stdout.write("\nEjemplo de reasignación (primeros 10):")
        for r, nuevo_valor in list(zip(registros, valores_nuevos))[:10]:
            self.stdout.write(
                f"  Reg {r.transaccion_id}: {r.ganancia_registrada}  ->  {nuevo_valor}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: NO se modificó la base de datos."
            ))
            return

        if not options["confirm"]:
            resp = input(
                "\nEsto va a SOBREESCRIBIR ganancia_registrada de TODOS los registros.\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        # 6) Aplicar cambios
        with transaction.atomic():
            for r, nuevo_valor in zip(registros, valores_nuevos):
                r.ganancia_registrada = nuevo_valor
                r.save(update_fields=["ganancia_registrada"])

        self.stdout.write(self.style.SUCCESS(
            f"\nValores de ganancias redistribuidos con éxito "
            f"para {total_registros} registros."
        ))
