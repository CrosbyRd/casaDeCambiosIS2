from django.core.management.base import BaseCommand
from django.db import transaction
from transacciones.models import Transaccion
from ganancias.models import RegistroGanancia
from monedas.models import Moneda
from decimal import Decimal

class Command(BaseCommand):
    help = 'Calcula y crea registros de ganancias para transacciones históricas completadas.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando cálculo de ganancias para transacciones históricas...'))

        with transaction.atomic():
            self.stdout.write(self.style.WARNING('Eliminando todos los registros de ganancias existentes...'))
            num_deleted, _ = RegistroGanancia.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Se eliminaron {num_deleted} registros de ganancias.'))

        try:
            moneda_pyg = Moneda.objects.get(codigo="PYG")
        except Moneda.DoesNotExist:
            self.stdout.write(self.style.ERROR("Error: Moneda PYG no encontrada. Asegúrate de que 'PYG' esté configurada en tus monedas."))
            return

        # Obtener todas las transacciones completadas
        transacciones_a_procesar = Transaccion.objects.filter(
            estado='completada'
        ).order_by('fecha_actualizacion') # Procesar en orden cronológico

        total_transacciones = transacciones_a_procesar.count()
        ganancias_creadas = 0

        if total_transacciones == 0:
            self.stdout.write(self.style.WARNING('No se encontraron transacciones completadas sin registros de ganancias pendientes de procesar.'))
            return

        self.stdout.write(f'Se encontraron {total_transacciones} transacciones para procesar.')

        with transaction.atomic():
            for i, instance in enumerate(transacciones_a_procesar):
                self.stdout.write(f'Procesando transacción {i+1}/{total_transacciones} (ID: {instance.id})...')

                moneda_operada = None
                if instance.tipo_operacion == 'venta':
                    moneda_operada = instance.moneda_destino
                elif instance.tipo_operacion == 'compra':
                    moneda_operada = instance.moneda_origen
                
                if not moneda_operada:
                    self.stdout.write(self.style.WARNING(f"Advertencia: Tipo de operación desconocido '{instance.tipo_operacion}' para Transaccion {instance.id}. Saltando."))
                    continue

                comision_bruta_registrada = instance.comision_cotizacion
                bonificacion_monto = instance.comision_aplicada
                comision_final = comision_bruta_registrada - bonificacion_monto

                monto_operado_para_ganancia = Decimal('0.00')
                if instance.tipo_operacion == 'venta':
                    monto_operado_para_ganancia = instance.monto_destino
                elif instance.tipo_operacion == 'compra':
                    monto_operado_para_ganancia = instance.monto_origen
                
                ganancia_neta_real = comision_final * monto_operado_para_ganancia

                RegistroGanancia.objects.create(
                    transaccion=instance,
                    ganancia_registrada=ganancia_neta_real,
                    moneda_ganancia=moneda_pyg,
                    moneda_operada=moneda_operada,
                    fecha_registro=instance.fecha_creacion # Usar fecha_creacion para la fecha original de la transacción
                )
                ganancias_creadas += 1
                self.stdout.write(self.style.SUCCESS(f"Registro de ganancia creado para Transaccion {instance.id}: {ganancia_neta_real} {moneda_pyg.codigo}"))

        self.stdout.write(self.style.SUCCESS(f'\nProceso completado. Se crearon {ganancias_creadas} nuevos registros de ganancias.'))
