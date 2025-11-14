from django.core.management.base import BaseCommand
from django.db import transaction
from transacciones.models import Transaccion
from ganancias.models import RegistroGanancia
from cotizaciones.models import Cotizacion
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalcula y actualiza el campo comision_cotizacion para transacciones históricas con valor 0, y elimina los registros de ganancia asociados.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando recalculo de comisiones históricas...'))

        # Transacciones a procesar: completadas y con comision_cotizacion en 0
        transacciones_a_recalcular = Transaccion.objects.filter(
            estado='completada',
            comision_cotizacion=Decimal('0.0000')
        ).order_by('fecha_actualizacion')

        total_transacciones = transacciones_a_recalcular.count()
        comisiones_actualizadas = 0
        registros_ganancia_eliminados = 0

        if total_transacciones == 0:
            self.stdout.write(self.style.WARNING('No se encontraron transacciones completadas con comision_cotizacion en 0 pendientes de recalcular.'))
            return

        self.stdout.write(f'Se encontraron {total_transacciones} transacciones para recalcular comisiones.')

        with transaction.atomic():
            for i, instance in enumerate(transacciones_a_recalcular):
                self.stdout.write(f'Procesando transacción {i+1}/{total_transacciones} (ID: {instance.id})...')

                # Eliminar RegistroGanancia existente si lo hay (ya que es incorrecto)
                if hasattr(instance, 'registro_ganancia'):
                    instance.registro_ganancia.delete()
                    registros_ganancia_eliminados += 1
                    self.stdout.write(f"  Registro de ganancia existente para Transaccion {instance.id} eliminado.")

                try:
                    cotizacion = None
                    if instance.tipo_operacion == 'venta':
                        # La casa de cambios vende divisa (PYG -> USD)
                        cotizacion = Cotizacion.objects.get(
                            moneda_base=instance.moneda_origen, # PYG
                            moneda_destino=instance.moneda_destino # USD
                        )
                        nueva_comision_cotizacion = cotizacion.comision_venta
                    elif instance.tipo_operacion == 'compra':
                        # La casa de cambios compra divisa (USD -> PYG)
                        cotizacion = Cotizacion.objects.get(
                            moneda_base=instance.moneda_destino, # PYG
                            moneda_destino=instance.moneda_origen # USD
                        )
                        nueva_comision_cotizacion = cotizacion.comision_compra
                    else:
                        self.stdout.write(self.style.WARNING(f"  Advertencia: Tipo de operación desconocido '{instance.tipo_operacion}' para Transaccion {instance.id}. Saltando recalculo de comisión."))
                        continue

                    if cotizacion:
                        instance.comision_cotizacion = nueva_comision_cotizacion
                        instance.save(update_fields=['comision_cotizacion'])
                        comisiones_actualizadas += 1
                        self.stdout.write(self.style.SUCCESS(f"  Comisión de cotización actualizada para Transaccion {instance.id} a: {nueva_comision_cotizacion}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  Advertencia: No se encontró cotización para Transaccion {instance.id}. Saltando recalculo de comisión."))

                except Cotizacion.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"  Error: No se encontró la cotización necesaria para recalcular la comisión de Transaccion {instance.id}. Saltando."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error inesperado al recalcular comisión para Transaccion {instance.id}: {e}. Saltando."))

        self.stdout.write(self.style.SUCCESS(f'\nProceso de recalculo completado.'))
        self.stdout.write(self.style.SUCCESS(f'Se actualizaron {comisiones_actualizadas} campos de comision_cotizacion.'))
        self.stdout.write(self.style.SUCCESS(f'Se eliminaron {registros_ganancia_eliminados} registros de ganancias incorrectos.'))
        self.stdout.write(self.style.WARNING('Ahora, por favor, ejecuta el comando "python manage.py calcular_ganancias_historicas" para recrear los registros de ganancias con los valores corregidos.'))
