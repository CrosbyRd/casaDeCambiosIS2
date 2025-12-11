from decimal import Decimal
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from transacciones.models import Transaccion


class Command(BaseCommand):
    help = (
        "Ajusta las transacciones por moneda para generar datos de prueba más realistas:\n"
        "  1) Borra la mitad de las transacciones COMPLETADAS con peso colombiano (COP).\n"
        "  2) Clona transacciones COMPLETADAS de alto monto (> umbral) que involucren USD.\n"
        "  3) Borra el 30% de las transacciones COMPLETADAS con peso chileno (CLP).\n"
        "Pensado solo para ENTORNO DE DESARROLLO."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "factor_usd",
            type=int,
            help=(
                "Factor de multiplicación para transacciones USD de alto monto. "
                "Ej: factor_usd=4 → crea 3 clones por cada transacción USD elegible."
            ),
        )
        parser.add_argument(
            "--umbral-monto",
            type=str,
            default="5000000",
            help="Umbral de monto (en Gs) para considerar una transacción de alto monto. "
                 "Por defecto: 5000000.",
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

    # ---------- Helper para campos únicos de tipo string ----------
    def _nuevo_valor_unico_str(self, field, nombre_campo, valor_original):
        """
        Genera un string nuevo para un CharField(unique=True), respetando max_length
        y asegurando que no exista en la tabla Transaccion.
        """
        max_len = field.max_length or 255

        base = ""
        if isinstance(valor_original, str) and max_len > 6:
            base = valor_original[: max_len - 6]  # dejamos espacio para sufijo

        for _ in range(10):
            sufijo = uuid.uuid4().hex[:6]  # 6 caracteres aleatorios
            candidato = (base + sufijo)[:max_len]
            if not Transaccion.objects.filter(**{nombre_campo: candidato}).exists():
                return candidato

        # Fallback extremo: solo random
        return uuid.uuid4().hex[:max_len]

    # ---------- Lógica principal ----------
    def handle(self, *args, **options):
        factor_usd = options["factor_usd"]
        if factor_usd < 2:
            raise CommandError("factor_usd debe ser al menos 2 (para generar clones).")

        clones_por_tx = factor_usd - 1
        umbral = Decimal(options["umbral_monto"])

        self.stdout.write(self.style.MIGRATE_HEADING("==> AJUSTE DE TRANSACCIONES POR MONEDA <=="))

        # 1) Transacciones COMPLETADAS con peso colombiano (COP)
        qs_cop = (
            Transaccion.objects
            .filter(estado="completada")
            .filter(
                Q(moneda_origen__codigo="COP") |
                Q(moneda_destino__codigo="COP")
            )
        )
        total_cop = qs_cop.count()
        borrar_cop = total_cop // 2

        # Elegimos las más recientes para borrar
        cop_a_borrar_ids = list(
            qs_cop.order_by("-fecha_creacion", "-pk")
            .values_list("pk", flat=True)[:borrar_cop]
        )

        # 2) Transacciones COMPLETADAS con USD y monto alto
        qs_usd = (
            Transaccion.objects
            .filter(estado="completada")
            .filter(
                Q(moneda_origen__codigo="USD") |
                Q(moneda_destino__codigo="USD")
            )
            .filter(
                Q(monto_origen__gt=umbral) |
                Q(monto_destino__gt=umbral)
            )
        )

        total_usd_alto = qs_usd.count()
        clones_esperados = total_usd_alto * clones_por_tx

        # 3) Transacciones COMPLETADAS con peso chileno (CLP)
        qs_clp = (
            Transaccion.objects
            .filter(estado="completada")
            .filter(
                Q(moneda_origen__codigo="CLP") |
                Q(moneda_destino__codigo="CLP")
            )
        )
        total_clp = qs_clp.count()
        borrar_clp = int(total_clp * 0.30)  # 30%

        clp_a_borrar_ids = list(
            qs_clp.order_by("-fecha_creacion", "-pk")
            .values_list("pk", flat=True)[:borrar_clp]
        )

        # ---------- Resumen previo ----------
        self.stdout.write("\n[RESUMEN PREVIO]")
        self.stdout.write(f"Transacciones COMPLETADAS con COP: {total_cop}")
        self.stdout.write(f"  → Se borrará la mitad: {borrar_cop}")
        self.stdout.write(f"Transacciones COMPLETADAS con CLP: {total_clp}")
        self.stdout.write(f"  → Se borrará el 30% aprox.: {borrar_clp}")
        self.stdout.write(f"Transacciones COMPLETADAS con USD y monto > {umbral}: {total_usd_alto}")
        self.stdout.write(
            f"  → factor_usd={factor_usd} → clones por tx: {clones_por_tx}, "
            f"total clones esperados: {clones_esperados}"
        )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN activado: NO se modificará la base de datos."
            ))
            return

        if not options["confirm"]:
            resp = input(
                "\nESTO VA A BORRAR Y CLONAR TRANSACCIONES (solo para datos de prueba).\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(self.style.ERROR("Operación cancelada por el usuario."))
                return

        # ---------- Aplicar cambios ----------
        creadas_usd = 0

        with transaction.atomic():
            # 1) Borrar COP
            if borrar_cop > 0:
                self.stdout.write("\nBorrando transacciones COMPLETADAS con COP (mitad)...")
                Transaccion.objects.filter(pk__in=cop_a_borrar_ids).delete()
            else:
                self.stdout.write("\nNo se borrarán transacciones COP (mitad = 0).")

            # 2) Clonar USD alto monto
            if total_usd_alto > 0:
                self.stdout.write(
                    f"\nClonando transacciones COMPLETADAS con USD y monto > {umbral}..."
                )
                for original in qs_usd:
                    for _ in range(clones_por_tx):
                        nueva = Transaccion()

                        for field in Transaccion._meta.fields:
                            nombre = field.name

                            # Saltar PK
                            if field.primary_key:
                                continue

                            # Saltar auto_now / auto_now_add
                            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                                continue

                            # Estas las seteamos manualmente
                            if nombre in ("fecha_creacion", "fecha_actualizacion"):
                                continue

                            valor = getattr(original, nombre)

                            # Campos únicos string → generar nuevo valor único
                            if getattr(field, "unique", False) and valor not in (None, ""):
                                if isinstance(valor, str):
                                    valor = self._nuevo_valor_unico_str(field, nombre, valor)
                                else:
                                    valor = None

                            setattr(nueva, nombre, valor)

                        ahora = timezone.now()
                        if hasattr(nueva, "fecha_creacion"):
                            nueva.fecha_creacion = ahora
                        if hasattr(nueva, "fecha_actualizacion"):
                            nueva.fecha_actualizacion = ahora

                        nueva.save()  # dispara señal de ganancias
                        creadas_usd += 1
            else:
                self.stdout.write("\nNo hay transacciones USD de alto monto para clonar.")

            # 3) Borrar CLP (30%)
            if borrar_clp > 0:
                self.stdout.write("\nBorrando 30% de transacciones COMPLETADAS con CLP...")
                Transaccion.objects.filter(pk__in=clp_a_borrar_ids).delete()
            else:
                self.stdout.write("\nNo se borrarán transacciones CLP (30% = 0).")

        # ---------- Resumen final ----------
        self.stdout.write(self.style.SUCCESS(
            "\nAjuste completado.\n"
            f"  - Transacciones COP eliminadas: {borrar_cop}\n"
            f"  - Transacciones CLP eliminadas: {borrar_clp}\n"
            f"  - Nuevas transacciones USD de alto monto creadas: {creadas_usd}\n"
        ))
