import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from configuracion.models import TransactionLimit

class Command(BaseCommand):
    help = "Crea configuración general desde fixture"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] /"configuracion"/ "fixtures" / "tipos_configuracion.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            conf_data = json.load(f)

        for item in conf_data:
            fields = item["fields"]
            pk = item.get("pk")
            conf, created = TransactionLimit.objects.update_or_create(
                id=pk,
                defaults={
                    "limite_diario": fields.get("limite_diario", 100000000),
                    "limite_mensual": fields.get("limite_mensual", 1000000000),
                    "activo": fields.get("activo", True)
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS("Configuración creada."))
            else:
                self.stdout.write(self.style.WARNING("Configuración actualizada."))
