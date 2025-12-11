from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cotizaciones.models import Cotizacion, CotizacionHistorica


class Command(BaseCommand):
    help = (
        "Crea cotizaciones históricas simuladas desde enero hasta diciembre para "
        "cada Cotizacion existente, con variaciones suaves en precios y comisiones.\n"
        "Pensado SOLO para datos de prueba (gráficos de cotizaciones)."
    )

    # ---------- helpers ----------

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=2025,
            help="Año a simular. Por defecto: 2025.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Seed para el generador aleatorio (para reproducir resultados).",
        )
        parser.add_argument(
            "--clear-year",
            action="store_true",
            help=(
                "Si se indica, borra antes todas las CotizacionHistorica "
                "de ese año para cada par de monedas."
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

    def _random_walk_step(
        self,
        mult_actual: Decimal,
        *,
        max_cambio_diario: Decimal,
        min_mult: Decimal,
        max_mult: Decimal,
    ) -> Decimal:
        """
        Aplica un cambio multiplicativo pequeño al factor actual
        y lo mantiene acotado entre [min_mult, max_mult].
        """
        delta_float = random.uniform(
            float(-max_cambio_diario), float(max_cambio_diario)
        )
        delta = Decimal(str(delta_float))
        nuevo = mult_actual * (Decimal("1.0") + delta)

        if nuevo < min_mult:
            nuevo = min_mult
        if nuevo > max_mult:
            nuevo = max_mult
        return nuevo

    def _base_comision(self, base_valor: Decimal, comision_actual: Decimal) -> Decimal:
        """
        Si la comisión actual es 0, inventamos una base como ~0.25% del valor.
        Si no, usamos la actual.
        """
        if comision_actual and comision_actual > 0:
            return comision_actual

        return (base_valor * Decimal("0.0025")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    # ---------- handle ----------

    def handle(self, *args, **options):
        year = options["year"]
        seed = options["seed"]
        clear_year = options["clear_year"]
        dry_run = options["dry_run"]

        if seed is not None:
            random.seed(seed)

        cotizaciones = list(
            Cotizacion.objects.select_related("moneda_base", "moneda_destino")
        )
        if not cotizaciones:
            self.stdout.write(
                self.style.WARNING("No hay Cotizacion definidas. Nada que simular.")
            )
            return

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 10)  # hasta el 10 de diciembre
        dias = (end_date - start_date).days + 1

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"==> SIEMBRA DE COTIZACIONES HISTÓRICAS PARA {year} <=="
            )
        )
        self.stdout.write(
            f"Total de pares de cotización encontrados: {len(cotizaciones)}"
        )
        self.stdout.write(
            f"Rango de fechas: {start_date} → {end_date} ({dias} días aprox.)"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN activado: solo se mostrará un resumen, sin tocar la base."
                )
            )

        # Preview rápida
        self.stdout.write("\nPares de monedas detectados (primeros 5):")
        for c in cotizaciones[:5]:
            self.stdout.write(
                f"  - {c.moneda_base.codigo} -> {c.moneda_destino.codigo}"
            )
        if len(cotizaciones) > 5:
            self.stdout.write(f"  ... y {len(cotizaciones) - 5} pares más.")

        if not dry_run and not options["confirm"]:
            resp = input(
                "\nEsto va a CREAR MUCHAS CotizacionHistorica (1 por día por par).\n"
                "Opcionalmente también borrará las existentes de ese año.\n"
                "Escribí 'SI' (en mayúsculas) para continuar: "
            )
            if resp.strip() != "SI":
                self.stdout.write(
                    self.style.ERROR("Operación cancelada por el usuario.")
                )
                return

        tz = timezone.get_current_timezone()
        total_creadas = 0
        total_borradas = 0

        if dry_run:
            self.stdout.write(
                "\n[Simulación únicamente, no se ejecutarán los cambios]\n"
            )

        # ---------- siembra ----------
        with transaction.atomic():
            for c in cotizaciones:
                pair_label = (
                    f"{c.moneda_base.codigo}->{c.moneda_destino.codigo}"
                )

                # Borrar historial previo de ese año si se pidió
                if clear_year and not dry_run:
                    borradas, _ = CotizacionHistorica.objects.filter(
                        moneda_base=c.moneda_base,
                        moneda_destino=c.moneda_destino,
                        fecha__date__gte=start_date,
                        fecha__date__lte=end_date,
                    ).delete()
                    total_borradas += borradas
                    self.stdout.write(
                        f"  [{pair_label}] Borradas {borradas} cotizaciones históricas de {year}."
                    )

                # ==== BASES: SIEMPRE USAMOS EL VALOR ACTUAL ====
                base_compra = c.valor_compra
                base_venta = c.valor_venta
                base_comi_compra = self._base_comision(
                    base_compra, c.comision_compra
                )
                base_comi_venta = self._base_comision(
                    base_venta, c.comision_venta
                )

                registros_nuevos = []

                # Empezamos EXACTAMENTE en el valor actual (día end_date)
                m_compra = Decimal("1.0")
                m_venta = Decimal("1.0")
                m_cc = Decimal("1.0")
                m_cv = Decimal("1.0")

                current = end_date
                while current >= start_date:
                    # Para el último día (end_date) no hacemos paso: se queda 1.0
                    if current != end_date:
                        # No hace falta que cambie todos los días:
                        # solo ~40% de los días se ajusta un poco.
                        if random.random() < 0.40:
                            m_compra = self._random_walk_step(
                                m_compra,
                                max_cambio_diario=Decimal("0.0015"),  # ~0,15 % por día
                                min_mult=Decimal("0.985"),           # -1,5 %
                                max_mult=Decimal("1.015"),           # +1,5 %
                            )
                        if random.random() < 0.40:
                            m_venta = self._random_walk_step(
                                m_venta,
                                max_cambio_diario=Decimal("0.0015"),
                                min_mult=Decimal("0.985"),
                                max_mult=Decimal("1.015"),
                            )
                        if random.random() < 0.30:
                            m_cc = self._random_walk_step(
                                m_cc,
                                max_cambio_diario=Decimal("0.004"),
                                min_mult=Decimal("0.90"),
                                max_mult=Decimal("1.10"),
                            )
                        if random.random() < 0.30:
                            m_cv = self._random_walk_step(
                                m_cv,
                                max_cambio_diario=Decimal("0.004"),
                                min_mult=Decimal("0.90"),
                                max_mult=Decimal("1.10"),
                            )

                    # Valores finales: SIEMPRE alrededor de la cotización ACTUAL
                    val_compra = (base_compra * m_compra).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                    val_venta = (base_venta * m_venta).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )

                    # Nunca 0 ni negativos
                    if val_compra <= 0:
                        val_compra = Decimal("1")
                    if val_venta <= 0:
                        val_venta = Decimal("1")

                    # Comisiones siguen siendo decimales finitos (están bien así)
                    comi_compra = (base_comi_compra * m_cc).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_UP
                    )
                    comi_venta = (base_comi_venta * m_cv).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_UP
                    )

                    if comi_compra <= 0:
                        comi_compra = Decimal("0.0001")
                    if comi_venta <= 0:
                        comi_venta = Decimal("0.0001")

                    dt = timezone.make_aware(
                        datetime(
                            current.year, current.month, current.day, 13, 0, 0
                        ),
                        tz,
                    )

                    registros_nuevos.append(
                        CotizacionHistorica(
                            moneda_base=c.moneda_base,
                            moneda_destino=c.moneda_destino,
                            valor_compra=val_compra,
                            comision_compra=comi_compra,
                            valor_venta=val_venta,
                            comision_venta=comi_venta,
                            fecha=dt,
                            fuente="simulado",
                        )
                    )

                    # caminamos un día hacia atrás
                    current -= timedelta(days=1)

                # Guardamos todo (el orden en la DB da igual)
                if dry_run:
                    self.stdout.write(
                        f"  [{pair_label}] Se crearían {len(registros_nuevos)} registros históricos."
                    )
                else:
                    CotizacionHistorica.objects.bulk_create(
                        registros_nuevos, batch_size=1000
                    )
                    total_creadas += len(registros_nuevos)
                    self.stdout.write(
                        f"  [{pair_label}] Creadas {len(registros_nuevos)} cotizaciones históricas simuladas."
                    )

            # fin for c

        # fin transaction

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN finalizado. No se creó ni borró ningún registro."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSiembra completada.\n"
                    f"  Cotizaciones históricas creadas: {total_creadas}\n"
                    f"  Cotizaciones históricas borradas (si clear-year): {total_borradas}\n"
                )
            )
