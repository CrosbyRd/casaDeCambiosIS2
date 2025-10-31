import json
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from monedas.models import Moneda
from cotizaciones.models import Cotizacion

# --- ### NUEVO ### ---
# Importamos la señal y el receptor (función) que la escucha
# Los nombres vienen del traceback que me mostraste
from cotizaciones.models import cotizacion_actualizada 
from notificaciones.signals import crear_notificacion_por_cambio_tasa
# ---------------------


class Command(BaseCommand):
    help = "Crea cotizaciones desde el fixture tasas.json"

    @transaction.atomic
    def handle(self, *args, **kwargs):

        # --- ### NUEVO ### ---
        # Desconectamos la señal ANTES de hacer nada
        cotizacion_actualizada.disconnect(crear_notificacion_por_cambio_tasa)
        self.stdout.write(self.style.WARNING("Señal de notificación (Celery/Redis) DESCONECTADA temporalmente."))
        # ---------------------

        try:
            fixture_path = Path(__file__).resolve().parents[3] / "cotizaciones" / "fixtures" / "tasas.json"
            if not fixture_path.exists():
                self.stdout.write(self.style.ERROR(f"No se encontró el fixture en {fixture_path}"))
                return

            with open(fixture_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                if item.get("model") != "cotizaciones.cotizacion":
                    continue

                fields = item["fields"]
                try:
                    moneda_base = Moneda.objects.get(codigo=fields["moneda_base"])
                    moneda_destino = Moneda.objects.get(codigo=fields["moneda_destino"])
                except Moneda.DoesNotExist as e:
                    self.stdout.write(self.style.WARNING(f"Moneda base o destino no encontrada ({e}). Saltando cotización."))
                    continue

                cotizacion, created = Cotizacion.objects.update_or_create(
                    moneda_base=moneda_base,
                    moneda_destino=moneda_destino,
                    defaults={
                        "valor_compra": Decimal(fields.get("valor_compra", "0")),
                        "valor_venta": Decimal(fields.get("valor_venta", "0")),
                        "comision_compra": Decimal(fields.get("comision_compra", "0")),
                        "comision_venta": Decimal(fields.get("comision_venta", "0")),
                    
                        # "fecha_actualizacion" se maneja automáticamente si no querés forzarla
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Cotización para '{moneda_destino.codigo}' creada."))
                else:
                    self.stdout.write(self.style.WARNING(f"Cotización para '{moneda_destino.codigo}' actualizada."))
        
        finally:
            # --- ### NUEVO ### ---
            # Envolvemos todo en try/finally para asegurarnos
            # de que la señal se RECONECTE siempre, incluso si hay un error.
            cotizacion_actualizada.connect(crear_notificacion_por_cambio_tasa)
            self.stdout.write(self.style.WARNING("Señal de notificación (Celery/Redis) RECONECTADA."))
            # ---------------------

        self.stdout.write(self.style.SUCCESS("Proceso de seed de cotizaciones finalizado."))