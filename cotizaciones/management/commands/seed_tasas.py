import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from monedas.models import Moneda
from cotizaciones.models import Cotizacion

class Command(BaseCommand):
    help = "Crea cotizaciones de ejemplo desde el fixture"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Usamos el fixture que parece contener las cotizaciones
        fixture_path = Path(__file__).resolve().parents[3] / "core" / "fixtures" / "monedas_cotizaciones.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Asumimos que la moneda base para todas las cotizaciones iniciales es Guaraní (PYG)
        try:
            moneda_base = Moneda.objects.get(codigo='PYG')
        except Moneda.DoesNotExist:
            self.stdout.write(self.style.ERROR("La moneda base 'PYG' no existe. Ejecuta 'seed_monedas' primero."))
            return

        for item in data:
            if item.get("model") == "monedas.moneda" and item["fields"]["codigo"] != "PYG":
                fields = item["fields"]
                try:
                    moneda_destino = Moneda.objects.get(codigo=fields["codigo"])
                    cotizacion, created = Cotizacion.objects.update_or_create(
                        moneda_base=moneda_base,
                        moneda_destino=moneda_destino,
                        defaults={
                            "valor_compra": fields.get("compra", 0),
                            "valor_venta": fields.get("venta", 0),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Cotización para '{moneda_destino.codigo}' creada."))
                    else:
                        self.stdout.write(self.style.WARNING(f"Cotización para '{moneda_destino.codigo}' actualizada."))
                except Moneda.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Moneda con código '{fields['codigo']}' no encontrada. Saltando cotización."))

        self.stdout.write(self.style.SUCCESS("Proceso de seed de tasas finalizado."))

