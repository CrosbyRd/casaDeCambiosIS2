from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from ganancias.models import RegistroGanancia
from transacciones.models import Transaccion
from cotizaciones.models import CotizacionHistorica   # 👈 NUEVO


class Command(BaseCommand):
    help = (
        "Redistribuye de forma UNIFORME las fechas de RegistroGanancia y "
        "CotizacionHistorica entre una fecha de inicio y una fecha de fin.\n"
        "Opcionalmente también ajusta fecha_creacion/fecha_actualizacion de Transaccion."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "start",
            nargs="?",
            type=str,
            default="2025-01-01",
            help="Fecha de inicio (YYYY-MM-DD). Por defecto: 2025-01-01",
        )
        parser.add_argument(
            "end",
            nargs="?",
            type=str,
            default=None,
            help=(
                "Fecha de fin (YYYY-MM-DD). "
                "Si no se indica, se usa 2025-12-10 por defecto."
            ),
        )
        parser.add_argument(
            "--update-transacciones",
            action="store_true",
            help=(
                "También mueve fecha_creacion y fecha_actualizacion de Transaccion "
                "para que coincidan con la nueva fecha de la ganancia."
            ),
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

    def _parse_dates(self, start_str, end_str, ejemplo_fecha):
        """
        Convierte los strings YYYY-MM-DD a datetimes coherentes con el tipo
        (aware/naive) de ejemplo_fecha.
        """
        # start
        try:
            naive_start = datetime.strptime(start_str, "%Y-%m-%d")
        except ValueError:
            raise CommandError("start debe tener formato YYYY-MM-DD, ej: 2025-01-01")

        # end
        if end_str:
            try:
                naive_end = datetime.strptime(end_str, "%Y-%m-%d")
            except ValueError:
                raise CommandError("end debe tener formato YYYY-MM-DD, ej: 2025-12-10")
        else:
            # 🔒 Por defecto, queremos que el rango termine el 10/12/2025
            naive_end = datetime(2025, 12, 10)

        # ponemos fin del día
        naive_end = naive_end.replace(hour=23, minute=59, second=59, microsecond=0)

        # ajustar aware/naive según ejemplo_fecha
        if timezone.is_aware(ejemplo_fecha):
            tz = timezone.get_current_timezone()
            start = timezone.make_aware(naive_start, tz)
            end = timezone.make_aware(naive_end, tz)
        else:
            start = naive_start
            end = naive_end.replace(tzinfo=None)

        if end <= start:
            raise CommandError("La fecha de fin debe ser posterior a la fecha de inicio.")

        return start, end

    def _calcular_steps(self, total, start, end):
        """
        Devuelve una lista de desplazamientos (en segundos) para repartir
        'total' puntos uniformemente entre start y end.
        """
        rango_segundos = (end - start).total_seconds()
        if total == 1:
            return [0]
        paso = rango_segundos / (total - 1)
        return [round(paso * i) for i in range(total)]

    def handle(self, *args, **options):
        # 1) Obtener ganancias y cotizaciones históricas
        ganancias = list(RegistroGanancia.objects.all())
        cotizaciones = list(CotizacionHistorica.objects.order_by("fecha"))

        total_g = len(ganancias)
        total_c = len(cotizaciones)

        if total_g == 0 and total_c == 0:
            self.stdout.write(self.style.WARNING(
                "No hay ni RegistroGanancia ni CotizacionHistorica. Nada que distribuir."
            ))
            return

        self.stdout.write(f"Total de registros de ganancia:         {total_g}")
        self.stdout.write(f"Total de cotizaciones históricas:       {total_c}")

        # Elegimos un ejemplo de fecha para manejar timezone
        if total_g > 0:
            ejemplo_fecha = ganancias[0].fecha_registro or timezone.now()
        else:
            ejemplo_fecha = cotizaciones[0].fecha

        start_str = options["start"]
        end_str = options["end"]
        start, end = self._parse_dates(start_str, end_str, ejemplo_fecha)

        self.stdout.write(f"\nRango objetivo para redistribuir:")
        self.stdout.write(f"  - Inicio: {start!r}")
        self.stdout.write(f"  - Fin:    {end!r}")

        # 2) SESGO SUAVE: valores más altos hacia OCT–NOV–DIC, pero no todos juntos

        mapeo_g = []  # (registro, fecha_vieja, fecha_nueva)

        if total_g > 0:
            # Ordenamos TODAS las ganancias por monto de menor a mayor
            ganancias_ordenadas = sorted(
                ganancias,
                key=lambda r: r.ganancia_registrada,
            )

            # Porcentaje de registros que queremos como "altos" en OCT–DIC
            porcentaje_altas = 0.1  # 40% más altos
            indice_altas = int(total_g * (1 - porcentaje_altas))
            if indice_altas < 0:
                indice_altas = 0
            if indice_altas > total_g:
                indice_altas = total_g

            bajas = ganancias_ordenadas[:indice_altas]   # 60% más chicas
            altas = ganancias_ordenadas[indice_altas:]   # 40% más grandes (ya ordenadas de menor a mayor)

            # Definimos rangos de fechas:
            # - bajas  → de start a 30/09/2025 (inclusive)
            # - altas  → de 01/10/2025 a end (10/12/2025)

            if timezone.is_aware(start):
                tzinfo = start.tzinfo
                oct_inicio = datetime(start.year, 10, 1, tzinfo=tzinfo)
                sep_fin = datetime(start.year, 9, 30, 23, 59, 59, tzinfo=tzinfo)
            else:
                oct_inicio = datetime(start.year, 10, 1)
                sep_fin = datetime(start.year, 9, 30, 23, 59, 59)

            rango_valido = (oct_inicio > start) and (sep_fin > start) and (end > oct_inicio)

            if not rango_valido or total_g < 3:
                # Fallback: todo uniforme
                steps_g = self._calcular_steps(total_g, start, end)
                for idx, reg in enumerate(ganancias_ordenadas):
                    nueva_fecha = start + timedelta(seconds=steps_g[idx])
                    mapeo_g.append((reg, reg.fecha_registro, nueva_fecha))
            else:
                # Bajas: de start a sep_fin (uniforme)
                if bajas:
                    steps_bajas = self._calcular_steps(len(bajas), start, sep_fin)
                    for idx, reg in enumerate(bajas):
                        nueva_fecha = start + timedelta(seconds=steps_bajas[idx])
                        mapeo_g.append((reg, reg.fecha_registro, nueva_fecha))

                # Altas: de oct_inicio a end (uniforme, valores de menor a mayor)
                if altas:
                    steps_altas = self._calcular_steps(len(altas), oct_inicio, end)
                    for idx, reg in enumerate(altas):  # ya vienen ordenadas de menor a mayor
                        nueva_fecha = oct_inicio + timedelta(seconds=steps_altas[idx])
                        mapeo_g.append((reg, reg.fecha_registro, nueva_fecha))

        # 3) Cotizaciones históricas: uniforme en todo el año
        steps_c = self._calcular_steps(total_c, start, end) if total_c > 0 else []
        mapeo_c = []
        for idx, reg in enumerate(cotizaciones):
            nueva_fecha = start + timedelta(seconds=steps_c[idx])
            mapeo_c.append((reg, reg.fecha, nueva_fecha))

        # 4) Preview de los primeros 5 de cada tipo
        self.stdout.write("\nEjemplo de reasignación de ganancias (primeros 5):")
        for reg, vieja, nueva in mapeo_g[:5]:
            self.stdout.write(f"  Ganancia ID {reg.pk}: {vieja}  ->  {nueva}")

        self.stdout.write("\nEjemplo de reasignación de cotizaciones históricas (primeros 5):")
        for reg, vieja, nueva in mapeo_c[:5]:
            self.stdout.write(f"  CotiHist ID {reg.pk}: {vieja}  ->  {nueva}")

        # 5) DRY RUN
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: NO se modificó la base de datos."
            ))
            return

        # 6) Confirmación
        if not options["confirm"]:
            resp = input(
                "\nEsto va a reescribir las fechas de TODOS los registros de "
                "RegistroGanancia y CotizacionHistorica.\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        # 👈 AQUÍ estaba el bug: debe ser update_transacciones (con guion bajo)
        update_trans = options["update_transacciones"]

        # 7) Aplicar cambios en una transacción
        with transaction.atomic():
            self.stdout.write("\nActualizando RegistroGanancia...")
            for reg, vieja, nueva in mapeo_g:
                RegistroGanancia.objects.filter(pk=reg.pk).update(
                    fecha_registro=nueva
                )
                if update_trans:
                    Transaccion.objects.filter(pk=reg.transaccion_id).update(
                        fecha_creacion=nueva,
                        fecha_actualizacion=nueva,
                    )

            self.stdout.write("Actualizando CotizacionHistorica...")
            for reg, vieja, nueva in mapeo_c:
                CotizacionHistorica.objects.filter(pk=reg.pk).update(
                    fecha=nueva
                )

        self.stdout.write(self.style.SUCCESS(
            "\nFechas redistribuidas con éxito. "
            "Las ganancias más altas se concentran en OCT–NOV–DIC, pero con un sesgo más suave."
        ))
