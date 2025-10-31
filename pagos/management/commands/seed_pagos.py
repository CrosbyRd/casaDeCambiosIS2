import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from pagos.models import TipoMedioPago

class Command(BaseCommand):
    help = "Crea o actualiza los tipos de medio de pago desde un fixture."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] / "pagos" / "fixtures" / "tipos_medio_pago.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            fields = item["fields"]
            # Limpiamos el nombre para que sea la clave de búsqueda fiable
            nombre_limpio = fields["nombre"].strip()

            medio, created = TipoMedioPago.objects.update_or_create(
                nombre=nombre_limpio,
                defaults={
                    "activo": fields.get("activo", True),
                    "comision_porcentaje": fields.get("comision_porcentaje", 0),
                    "descripcion": fields.get("descripcion", "").strip(),
                    "engine": fields.get("engine", "manual").strip(), # Limpiamos el engine también
                    "engine_config": fields.get("engine_config", {}),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Tipo de medio de pago '{medio.nombre}' creado."))
            else:
                self.stdout.write(self.style.WARNING(f"Tipo de medio de pago '{medio.nombre}' actualizado."))

        self.stdout.write(self.style.SUCCESS("Proceso de seed de tipos de pago finalizado."))
