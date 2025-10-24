from django.core.management.base import BaseCommand
from medios_acreditacion.models import MedioAcreditacionCliente, TipoMedioAcreditacion
import json
from pathlib import Path
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = "Crea o actualiza los medios de acreditación de clientes desde fixture"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fixture_path = Path(__file__).resolve().parents[3] / "medios_acreditacion" / "fixtures" / "medios_acreditacion.json"

        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Primero, crear o actualizar los Tipos de Medio de Acreditación
        for item in data:
            if item["model"] == "medios_acreditacion.tipomedioacreditacion":
                fields = item["fields"]
                pk = item["pk"]
                TipoMedioAcreditacion.objects.update_or_create(
                    id_tipo=pk,
                    defaults={
                        "nombre": fields["nombre"],
                        "descripcion": fields.get("descripcion", ""),
                        "activo": fields.get("activo", True),
                    }
                )
        self.stdout.write(self.style.SUCCESS("Tipos de medios de acreditación procesados."))

        # Segundo, crear o actualizar los Medios de Acreditación de Clientes
        for item in data:
            if item["model"] == "medios_acreditacion.medioacreditacioncliente":
                fields = item["fields"]
                try:
                    tipo = TipoMedioAcreditacion.objects.get(pk=fields["tipo"])
                    medio, created = MedioAcreditacionCliente.objects.update_or_create(
                        cliente_id=fields["cliente"],
                        tipo=tipo,
                        defaults={
                            "alias": fields.get("alias", ""),
                            "datos": fields.get("datos", {}),
                            "activo": fields.get("activo", True),
                            "predeterminado": fields.get("predeterminado", False),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Medio '{medio.alias}' para cliente '{medio.cliente_id}' creado."))
                    else:
                        self.stdout.write(self.style.WARNING(f"Medio '{medio.alias}' para cliente '{medio.cliente_id}' actualizado."))
                except ObjectDoesNotExist:
                    self.stdout.write(self.style.ERROR(f"No existe TipoMedioAcreditacion con ID {fields['tipo']} para el medio del cliente."))

        self.stdout.write(self.style.SUCCESS("Proceso de seed de medios de acreditación finalizado."))
