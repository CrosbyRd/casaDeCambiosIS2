from decimal import Decimal
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from transacciones.models import Transaccion


class Command(BaseCommand):
    help = (
        "Clona transacciones con estado 'completada' para generar más datos "
        "de prueba y así aumentar la cantidad de registros de ganancias.\n"
        "En esta versión SOLO se clonan las transacciones cuyo monto (origen o "
        "destino) sea mayor a 5.000.000 Gs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "factor",
            type=int,
            help=(
                "Factor total de multiplicación. "
                "Ej: factor=3 genera 2 clones por cada transacción elegible."
            ),
        )
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

    def _nuevo_valor_unico_str(self, field, nombre_campo, valor_original):
        """
        Genera un string nuevo para un CharField(unique=True), respetando max_length
        y asegurando que no exista en la tabla Transaccion.
        """
        max_len = field.max_length or 255

        # Si queremos conservar algo del valor original
        base = ""
        if isinstance(valor_original, str) and max_len > 6:
            base = valor_original[: max_len - 6]  # dejamos espacio para sufijo

        # Intentamos unos cuantos candidatos hasta que no exista
        for _ in range(10):
            sufijo = uuid.uuid4().hex[:6]  # 6 chars aleatorios
            candidato = (base + sufijo)[:max_len]
            if not Transaccion.objects.filter(**{nombre_campo: candidato}).exists():
                return candidato

        # Fallback extremo: solo random
        return uuid.uuid4().hex[:max_len]

    def handle(self, *args, **options):
        factor = options["factor"]
        if factor < 2:
            raise CommandError("El factor debe ser al menos 2 (para generar clones).")

        clones_por_tx = factor - 1

        # 🔥 SOLO transacciones COMPLETADAS con monto grande (> 5.000.000 Gs)
        umbral = Decimal("5000000")
        base_qs = (
            Transaccion.objects
            .filter(estado="completada")
            .filter(
                Q(monto_origen__gt=umbral) |
                Q(monto_destino__gt=umbral)
            )
        )

        total_base = base_qs.count()

        if total_base == 0:
            self.stdout.write(self.style.WARNING(
                f"No hay transacciones 'completada' con monto > {umbral} Gs. "
                "Nada que clonar."
            ))
            return

        self.stdout.write(
            f"Transacciones COMPLETADAS con monto > {umbral} encontradas: {total_base}\n"
            f"Se crearán {clones_por_tx} clones por cada una "
            f"(total clones esperados: {total_base * clones_por_tx})."
        )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: NO se creará ninguna transacción."
            ))
            return

        if not options["confirm"]:
            resp = input(
                "\nESTO CREARÁ NUEVAS TRANSACCIONES de ALTO MONTO (solo para datos de prueba).\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        creadas = 0

        # ⚠️ Importante: esto se debe correr en entorno de DESARROLLO
        with transaction.atomic():
            for original in base_qs:
                for idx in range(clones_por_tx):
                    nueva = Transaccion()

                    for field in Transaccion._meta.fields:
                        nombre = field.name

                        # Saltar PK
                        if field.primary_key:
                            continue

                        # Saltar auto_now / auto_now_add
                        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                            continue

                        # Estas las seteamos nosotros
                        if nombre in ("fecha_creacion", "fecha_actualizacion"):
                            continue

                        valor = getattr(original, nombre)

                        # ⚠️ Campos únicos (unique=True) tipo string
                        if getattr(field, "unique", False) and valor not in (None, ""):
                            if isinstance(valor, str):
                                valor = self._nuevo_valor_unico_str(field, nombre, valor)
                            else:
                                # Para tipos únicos no string (si hubiera), mejor dejar None
                                valor = None

                        setattr(nueva, nombre, valor)

                    # Timestamps “realistas” para el clone
                    ahora = timezone.now()
                    if hasattr(nueva, "fecha_creacion"):
                        nueva.fecha_creacion = ahora
                    if hasattr(nueva, "fecha_actualizacion"):
                        nueva.fecha_actualizacion = ahora

                    nueva.save()  # 🔔 dispara la señal de ganancias

                    creadas += 1

            self.stdout.write(self.style.SUCCESS(
                f"\nTransacciones clonadas con éxito. Nuevas transacciones creadas: {creadas}."
            ))
