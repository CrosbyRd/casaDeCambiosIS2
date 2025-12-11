from decimal import Decimal, ROUND_HALF_UP
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from ganancias.models import RegistroGanancia


class Command(BaseCommand):
    help = (
        "Redistribuye los valores de ganancia_registrada de forma MUY variable, "
        "para que el gráfico sea más 'puntiagudo' (muchos valores pequeños y "
        "algunos picos grandes), manteniendo aproximadamente el total."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--alpha",
            type=float,
            default=0.6,
            help=(
                "Parámetro de forma para la distribución tipo Gamma/Dirichlet. "
                "Valores más pequeños (<1) generan distribuciones más 'picosas'. "
                "Por defecto: 0.6"
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
        alpha = options["alpha"]
        seed = options["seed"]
        dry_run = options["dry_run"]

        if alpha <= 0:
            self.stdout.write(self.style.ERROR("alpha debe ser > 0."))
            return

        if seed is not None:
            random.seed(seed)

        registros = list(RegistroGanancia.objects.order_by("fecha_registro", "pk"))
        n = len(registros)

        if n == 0:
            self.stdout.write(self.style.WARNING("No hay registros de RegistroGanancia."))
            return

        # Total actual de ganancias (lo queremos conservar)
        total_actual = sum(
            (r.ganancia_registrada for r in registros),
            Decimal("0.00"),
        )

        self.stdout.write(self.style.MIGRATE_HEADING(
            "==> REDISTRIBUCIÓN 'SPIKY' DE GANANCIAS <=="
        ))
        self.stdout.write(f"Cantidad de registros: {n}")
        self.stdout.write(f"Total actual de ganancias: {total_actual}")

        # 1) Generamos pesos muy desiguales usando Gamma(alpha, 1)
        pesos = []
        for _ in range(n):
            # gammavariate(k, theta) → usamos theta=1.0
            w = Decimal(str(random.gammavariate(alpha, 1.0)))
            if w <= 0:
                w = Decimal("0.000001")
            pesos.append(w)

        suma_pesos = sum(pesos, Decimal("0.0"))
        if suma_pesos <= 0:
            self.stdout.write(self.style.ERROR(
                "La suma de pesos resultó cero. Revisar alpha/aleatoriedad."
            ))
            return

        # 2) Convertimos pesos en montos, preservando el total
        valores_nuevos = []
        for w in pesos:
            proporcion = w / suma_pesos
            nuevo = (total_actual * proporcion).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            valores_nuevos.append(nuevo)

        # 3) Ajustamos por diferencias de redondeo
        suma_nueva = sum(valores_nuevos, Decimal("0.00"))
        diferencia = (total_actual - suma_nueva).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if diferencia != 0 and n > 0:
            # Metemos toda la diferencia en el último registro
            valores_nuevos[-1] = (valores_nuevos[-1] + diferencia).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # 4) Evitar valores exactamente 0
        valores_nuevos = [
            v if v > Decimal("0.00") else Decimal("0.01") for v in valores_nuevos
        ]

        # 5) Preview
        self.stdout.write("\nEjemplo de reasignación (primeros 10 registros):")
        for reg, nuevo_valor in list(zip(registros, valores_nuevos))[:10]:
            self.stdout.write(
                f"  Reg transaccion={reg.transaccion_id}: "
                f"{reg.ganancia_registrada}  ->  {nuevo_valor}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: NO se modificó la base de datos."
            ))
            return

        if not options["confirm"]:
            resp = input(
                "\nEsto va a SOBREESCRIBIR ganancia_registrada para TODOS los registros.\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        # 6) Aplicar cambios
        with transaction.atomic():
            for reg, nuevo_valor in zip(registros, valores_nuevos):
                reg.ganancia_registrada = nuevo_valor
                reg.save(update_fields=["ganancia_registrada"])

        self.stdout.write(self.style.SUCCESS(
            "\nRedistribución 'spiky' aplicada con éxito. "
            "El gráfico debería mostrar muchas ganancias chicas y algunos picos grandes."
        ))
