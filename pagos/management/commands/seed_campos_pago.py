# pagos/management/commands/seed_campos_pago.py
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from pagos.models import CampoMedioPago, TipoMedioPago

class Command(BaseCommand):
    help = "Crea o actualiza los campos dinámicos de medios de pago."

    # Mapa legacy (si tus fixtures usan p1, p2, etc.)
    LEGACY_MAP = {
        "p1": "Transferencia Bancaria",
        "p2": "Tarjeta de Crédito",
        "p3": "Billetera Electrónica",
        "p4": "Tarjeta de Debito",
        "p5": "Stripe"
    }

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] / "pagos" / "fixtures" / "campos_medio_pago.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            fields = item.get("fields", {})
            tipo_ref = fields.get("tipo") or fields.get("tipo_nombre")
            if not tipo_ref:
                self.stdout.write(self.style.ERROR(f"Item sin referencia de tipo: {item}"))
                continue

            tipo = None

            # 1) Intentar por pk (UUID)
            try:
                tipo = TipoMedioPago.objects.get(pk=tipo_ref)
            except Exception:
                tipo = None

            # 2) Intentar por nombre exacto/insensible a mayúsculas
            if tipo is None:
                try:
                    tipo = TipoMedioPago.objects.get(nombre__iexact=str(tipo_ref).strip())
                except TipoMedioPago.DoesNotExist:
                    tipo = None

            # 3) Intentar legacy map (p1 -> nombre)
            if tipo is None and str(tipo_ref) in self.LEGACY_MAP:
                nombre = self.LEGACY_MAP[str(tipo_ref)]
                try:
                    tipo = TipoMedioPago.objects.get(nombre__iexact=nombre)
                except TipoMedioPago.DoesNotExist:
                    tipo = None

            if tipo is None:
                self.stdout.write(self.style.ERROR(f"No se pudo resolver TipoMedioPago para referencia '{tipo_ref}'."))
                continue

            # Crear/actualizar el campo
            try:
                campo, created = CampoMedioPago.objects.update_or_create(
                    tipo=tipo,
                    nombre_campo=fields["nombre_campo"],
                    defaults={
                        "tipo_dato": fields.get("tipo_dato", "texto"),
                        "obligatorio": fields.get("obligatorio", False),
                        "regex_opcional": fields.get("regex_opcional", "") or "",
                        "activo": fields.get("activo", True),
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Campo '{campo.nombre_campo}' creado para {tipo.nombre}."))
                else:
                    self.stdout.write(self.style.WARNING(f"Campo '{campo.nombre_campo}' actualizado para {tipo.nombre}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al crear/actualizar campo '{fields.get('nombre_campo')}' para tipo '{tipo.nombre}': {e}"))

        self.stdout.write(self.style.SUCCESS("Proceso de seed de campos de medios de pago finalizado."))
