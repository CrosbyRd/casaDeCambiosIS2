import json
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from pagos.models import TipoMedioPago

class Command(BaseCommand):
    help = "Crea o actualiza los tipos de medio de pago desde un fixture."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] / "pagos" / "fixtures" / "tipos_medio_pago.json"
        
        # --- Este bloque carga el archivo JSON ---
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # --- Fin del bloque de carga ---

        # Itera sobre los datos cargados
        for item in data:
            fields = item["fields"]
            nombre_limpio = fields["nombre"].strip()

            # Usa update_or_create para evitar duplicados
            medio, created = TipoMedioPago.objects.update_or_create(
                nombre__iexact=nombre_limpio,  # Busca sin importar mayúsculas
                defaults={
                    "nombre": nombre_limpio, # Guarda el nombre "limpio"
                    "activo": fields.get("activo", True),
                    "comision_porcentaje": fields.get("comision_porcentaje", 0),
                    "descripcion": fields.get("descripcion", "").strip(),
                    "engine": fields.get("engine", "manual").strip(),
                    "engine_config": fields.get("engine_config", {}),
                    
                    # El campo obligatorio que faltaba
                    "bonificacion_porcentaje": fields.get("bonificacion_porcentaje", Decimal("0.0")),
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"Tipo de medio de pago '{medio.nombre}' creado."))
            else:
                self.stdout.write(self.style.WARNING(f"Tipo de medio de pago '{medio.nombre}' actualizado."))

        self.stdout.write(self.style.SUCCESS("Proceso de seed de tipos de pago finalizado."))