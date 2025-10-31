import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from ted.models import TedTerminal
from monedas.models import Moneda, TedDenominacion, TedInventario


class Command(BaseCommand):
    help = "Carga datos iniciales para el módulo TED (Terminal de Efectivo Digital)."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "ted.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            model_name = item.get("model")
            fields = item.get("fields", {})

            # --- Terminales ---
            if model_name == "ted.tedterminal":
                terminal, created = TedTerminal.objects.update_or_create(
                    serial=fields.get("serial"),
                    defaults={
                        "direccion": fields.get("direccion"),
                        "created_at": timezone.datetime.fromisoformat(fields.get("created_at", timezone.now().isoformat()).replace("Z", "+00:00")),
                        "updated_at": timezone.datetime.fromisoformat(fields.get("updated_at", timezone.now().isoformat()).replace("Z", "+00:00")),
                    },
                )
                msg = f"Terminal TED '{terminal.serial}' {'creada' if created else 'actualizada'}."
                self.stdout.write(self.style.SUCCESS(msg) if created else self.style.WARNING(msg))

            # --- Denominaciones ---
            elif model_name == "monedas.teddenominacion":
                moneda_codigo = fields.get("moneda_codigo")
                if not moneda_codigo:
                    self.stdout.write(self.style.ERROR("Falta 'moneda_codigo' en el registro de denominación."))
                    continue

                try:
                    moneda = Moneda.objects.get(codigo=moneda_codigo)
                except Moneda.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Moneda '{moneda_codigo}' no encontrada."))
                    continue

                denominacion, created = TedDenominacion.objects.update_or_create(
                    moneda=moneda,
                    valor=fields.get("valor"),
                    defaults={"activa": fields.get("activa", True)},
                )
                msg = f"Denominación {denominacion.moneda.codigo} {denominacion.valor} {'creada' if created else 'actualizada'}."
                self.stdout.write(self.style.SUCCESS(msg) if created else self.style.WARNING(msg))

            # --- Inventario ---
            elif model_name == "monedas.tedinventario":
                moneda_codigo = fields.get("moneda_codigo")
                valor_denominacion = fields.get("valor_denominacion")
                if not moneda_codigo or valor_denominacion is None:
                    self.stdout.write(self.style.ERROR(f"Falta 'moneda_codigo' o 'valor_denominacion' en inventario."))
                    continue

                try:
                    moneda = Moneda.objects.get(codigo=moneda_codigo)
                    denominacion = TedDenominacion.objects.get(moneda=moneda, valor=valor_denominacion)
                except (Moneda.DoesNotExist, TedDenominacion.DoesNotExist):
                    self.stdout.write(self.style.ERROR(f"No se encontró denominación para {moneda_codigo} {valor_denominacion}"))
                    continue

                inventario, created = TedInventario.objects.update_or_create(
                    denominacion=denominacion,
                    ubicacion=fields.get("ubicacion"),
                    defaults={
                        "cantidad": fields.get("cantidad", 0),
                        "updated_at": timezone.datetime.fromisoformat(fields.get("updated_at", timezone.now().isoformat()).replace("Z", "+00:00")),
                    },
                )
                msg = f"Inventario {denominacion.moneda.codigo} {denominacion.valor} en '{inventario.ubicacion}' {'creado' if created else 'actualizado'}."
                self.stdout.write(self.style.SUCCESS(msg) if created else self.style.WARNING(msg))

        self.stdout.write(self.style.SUCCESS("✅ Proceso de seed de datos TED finalizado correctamente."))
