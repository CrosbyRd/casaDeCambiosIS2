import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from clientes.models import Cliente

class Command(BaseCommand):
    help = "Crea clientes de ejemplo desde el fixture"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] / "clientes" / "fixtures" / "clientes.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            clientes_data = json.load(f)

        for item in clientes_data:
            fields = item["fields"]
            pk = item.get("pk")
            cliente, created = Cliente.objects.update_or_create(
                id_cliente=pk,
                defaults={
                    "nombre": fields["nombre"],
                    "categoria": fields["categoria"],
                    "activo": fields["activo"],
                    "fecha_registro": fields.get("fecha_registro"),
                    "ultima_modificacion": fields.get("ultima_modificacion"),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Cliente '{cliente.nombre}' creado."))
            else:
                self.stdout.write(self.style.WARNING(f"Cliente '{cliente.nombre}' actualizado."))
