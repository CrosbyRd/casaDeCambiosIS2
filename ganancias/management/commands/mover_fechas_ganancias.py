from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from ganancias.models import RegistroGanancia
from transacciones.models import Transaccion
from cotizaciones.models import CotizacionHistorica


class Command(BaseCommand):
    help = (
        "Desplaza en bloque las fechas de RegistroGanancia, "
        "y opcionalmente Transaccion y CotizacionHistorica, "
        "para simular histórico desde una fecha dada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "target_start",
            nargs="?",
            type=str,
            default="2025-01-01",
            help="Fecha desde la que querés que empiece la serie (YYYY-MM-DD). "
                 "Por defecto: 2025-01-01.",
        )
        parser.add_argument(
            "--solo-ganancias",
            action="store_true",
            help="Solo mueve RegistroGanancia, sin tocar Transaccion ni CotizacionHistorica.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra lo que se haría, sin modificar la base de datos.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="No pedir confirmación interactiva (útil para scripts).",
        )

    def handle(self, *args, **options):
        # 1) Obtener primera ganancia para calcular el delta
        primero = RegistroGanancia.objects.order_by("fecha_registro").first()
        if not primero:
            self.stdout.write(self.style.WARNING(
                "No hay registros en RegistroGanancia. Nada que mover."
            ))
            return

        primera_fecha = primero.fecha_registro
        self.stdout.write(f"Primera fecha actual de ganancias: {primera_fecha!r}")

        # 2) Parsear fecha objetivo
        target_str = options["target_start"]
        try:
            naive_target = datetime.strptime(target_str, "%Y-%m-%d")
        except ValueError:
            raise CommandError(
                "target_start debe tener formato YYYY-MM-DD, por ejemplo: 2025-01-01"
            )

        # Adaptar a zona horaria si las fechas actuales son 'aware'
        if timezone.is_aware(primera_fecha):
            target_start = timezone.make_aware(
                naive_target, timezone.get_current_timezone()
            )
        else:
            target_start = naive_target

        delta = primera_fecha - target_start
        if delta.total_seconds() == 0:
            self.stdout.write(self.style.WARNING(
                "La primera fecha ya coincide con target_start. No se requiere ajuste."
            ))
            return

        self.stdout.write(f"Delta a restar a todas las fechas: {delta}")

        # 3) Contar registros
        total_ganancias = RegistroGanancia.objects.count()
        total_trans = Transaccion.objects.count()
        total_hist = CotizacionHistorica.objects.count()

        self.stdout.write(
            f"Registros a afectar:\n"
            f"  - RegistroGanancia:     {total_ganancias}\n"
            f"  - Transaccion:          {total_trans}\n"
            f"  - CotizacionHistorica:  {total_hist}"
        )

        # 4) DRY RUN → solo mostrar info y salir
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "DRY RUN activado: no se modificó ninguna fecha."
            ))
            return

        # 5) Confirmación manual (si no se pasa --confirm)
        if not options["confirm"]:
            respuesta = input(
                "\nESTO MOVERÁ TODAS LAS FECHAS ANTERIORES.\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if respuesta.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        # 6) Actualizar en bloque, dentro de una transacción
        with transaction.atomic():
            self.stdout.write("Actualizando RegistroGanancia...")
            RegistroGanancia.objects.update(
                fecha_registro=F("fecha_registro") - delta
            )

            if not options["solo_ganancias"]:
                self.stdout.write("Actualizando Transaccion (fechas de creación/actualización)...")
                Transaccion.objects.update(
                    fecha_creacion=F("fecha_creacion") - delta,
                    fecha_actualizacion=F("fecha_actualizacion") - delta,
                )

                self.stdout.write("Actualizando CotizacionHistorica...")
                CotizacionHistorica.objects.update(
                    fecha=F("fecha") - delta
                )

        self.stdout.write(self.style.SUCCESS("Fechas desplazadas correctamente."))
