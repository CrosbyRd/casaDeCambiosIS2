import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from transacciones.models import Transaccion


class Command(BaseCommand):
    help = (
        "Borra la MITAD de las transacciones COMPLETADAS que involucren "
        "USD (ya sea como moneda de origen o de destino).\n"
        "Pensado SOLO para datos de prueba en entorno de DESARROLLO."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué se haría, pero SIN modificar la base de datos.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="No pedir confirmación interactiva (útil para scripts).",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "==> BORRAR MITAD DE TRANSACCIONES USD <=="
        ))

        # 1) Buscamos transacciones COMPLETADAS con USD en origen o destino
        qs_usd = (
            Transaccion.objects
            .filter(estado="completada")
            .filter(
                Q(moneda_origen__codigo="USD") |
                Q(moneda_destino__codigo="USD")
            )
        )

        total_usd = qs_usd.count()
        if total_usd == 0:
            self.stdout.write(self.style.WARNING(
                "No hay transacciones COMPLETADAS con USD. Nada que borrar."
            ))
            return

        borrar = total_usd // 2  # mitad (redondeo hacia abajo)
        if borrar == 0:
            self.stdout.write(self.style.WARNING(
                f"Solo hay {total_usd} transacciones USD. Mitad=0, no se borrará nada."
            ))
            return

        # Tomamos IDs y elegimos aleatoriamente la mitad a borrar
        ids_usd = list(qs_usd.values_list("pk", flat=True))
        ids_a_borrar = set(random.sample(ids_usd, borrar))

        self.stdout.write("\n[RESUMEN PREVIO]")
        self.stdout.write(f"Transacciones COMPLETADAS con USD encontradas: {total_usd}")
        self.stdout.write(f"Se borrará la mitad (aprox): {borrar}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: NO se borrará nada en la base de datos."
            ))
            return

        if not options["confirm"]:
            resp = input(
                "\nESTO VA A BORRAR TRANSACCIONES COMPLETADAS EN USD "
                "(y sus registros de ganancia asociados).\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        # 2) Borrado dentro de una transacción
        with transaction.atomic():
            borradas, _ = Transaccion.objects.filter(pk__in=ids_a_borrar).delete()

        self.stdout.write(self.style.SUCCESS(
            f"\nBorrado completado. Filas afectadas (incluye relacionadas): {borradas}.\n"
            f"Transacciones USD eliminadas: {borrar} (aprox. la mitad)."
        ))
