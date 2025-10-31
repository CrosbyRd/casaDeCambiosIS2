import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from medios_acreditacion.models import CampoMedioAcreditacion, TipoMedioAcreditacion

class Command(BaseCommand):
    help = "Crea o actualiza los campos dinámicos de los tipos de medios de acreditación."

    LEGACY_MAP = {
        "11111111-1111-1111-1111-111111111111": "Cuenta bancaria",
        "22222222-2222-2222-2222-222222222222": "Tarjeta de débito",
        "33333333-3333-3333-3333-333333333333": "Billetera Electrónica"
    }

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] / "medios_acreditacion" / "fixtures" / "campos_medio_acreditacion.json"

        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            fields = item.get("fields", {})
            tipo_ref = fields.get("tipo_medio")

            tipo = None

            # 1️⃣ Buscar por UUID directamente
            try:
                tipo = TipoMedioAcreditacion.objects.get(pk=tipo_ref)
            except TipoMedioAcreditacion.DoesNotExist:
                pass

            # 2️⃣ Buscar por nombre si no se encontró
            if tipo is None and tipo_ref in self.LEGACY_MAP:
                nombre = self.LEGACY_MAP[tipo_ref]
                try:
                    tipo = TipoMedioAcreditacion.objects.get(nombre__iexact=nombre)
                except TipoMedioAcreditacion.DoesNotExist:
                    tipo = None

            if tipo is None:
                self.stdout.write(self.style.ERROR(f"No se pudo resolver TipoMedioAcreditacion para referencia '{tipo_ref}'."))
                continue

            try:
                campo, created = CampoMedioAcreditacion.objects.update_or_create(
                    tipo_medio=tipo,
                    nombre=fields["nombre"],
                    defaults={
                        "tipo_dato": fields.get("tipo_dato", "texto"),
                        "obligatorio": fields.get("obligatorio", False),
                        "regex": fields.get("regex", ""),
                        "activo": fields.get("activo", True),
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Campo '{campo.nombre}' creado para {tipo.nombre}."))
                else:
                    self.stdout.write(self.style.WARNING(f"Campo '{campo.nombre}' actualizado para {tipo.nombre}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al procesar campo '{fields.get('nombre')}' para tipo '{tipo.nombre}': {e}"))


        self.stdout.write(self.style.SUCCESS("✅ Proceso de seed de campos de medios de acreditación finalizado."))
