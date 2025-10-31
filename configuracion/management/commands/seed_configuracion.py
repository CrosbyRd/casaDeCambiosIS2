import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from configuracion.models import TransactionLimit
from monedas.models import Moneda
from django.core.exceptions import ObjectDoesNotExist

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
            if item.get("model") == "configuracion.transactionlimit":
                fields = item["fields"]
                moneda_codigo = fields.get("moneda_codigo")

                if not moneda_codigo:
                    self.stdout.write(self.style.ERROR("El fixture de configuración tiene un item sin 'moneda_codigo' definido. Saltando..."))
                    continue

                try:
                    moneda = Moneda.objects.get(codigo=moneda_codigo)
                    conf, created = TransactionLimit.objects.update_or_create(
                        moneda=moneda,
                        defaults={
                            "monto_diario": fields.get("monto_diario", 100000000),
                            "monto_mensual": fields.get("monto_mensual", 1000000000),
                            "aplica_diario": fields.get("aplica_diario", True),
                            "aplica_mensual": fields.get("aplica_mensual", True),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Límite de transacción para {moneda.codigo} creado."))
                    else:
                        self.stdout.write(self.style.WARNING(f"Límite de transacción para {moneda.codigo} actualizado."))
                except ObjectDoesNotExist:
                    self.stdout.write(self.style.ERROR(f"No se encontró la moneda con código '{moneda_codigo}'. Asegúrate de ejecutar 'seed_monedas' primero."))
        
        self.stdout.write(self.style.SUCCESS("Proceso de seed de configuración finalizado."))
