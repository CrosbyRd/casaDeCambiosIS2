import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from monedas.models import Moneda

class Command(BaseCommand):
    help = "Crea monedas desde fixture"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] /"monedas"/ "fixtures" / "monedas.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            monedas_data = json.load(f)

        for item in monedas_data:
            fields = item["fields"]
            moneda, created = Moneda.objects.update_or_create(
                codigo=fields["codigo"],
                defaults={
                    "nombre": fields["nombre"],
                    "codigo": fields["codigo"],
                    "simbolo": fields["simbolo"],
                    "admite_en_linea": fields["activo"],
                    "admite_terminal": fields["activo"],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Moneda '{moneda.nombre}' creada."))
            else:
                self.stdout.write(self.style.WARNING(f"Moneda '{moneda.nombre}' actualizada."))
