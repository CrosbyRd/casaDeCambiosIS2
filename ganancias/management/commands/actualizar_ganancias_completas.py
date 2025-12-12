from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Ejecuta los comandos recalcular_comisiones_historicas y calcular_ganancias_historicas en orden.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando proceso de actualización completa de ganancias...'))

        self.stdout.write(self.style.SUCCESS('1. Ejecutando recalcular_comisiones_historicas...'))
        try:
            call_command('recalcular_comisiones_historicas')
            self.stdout.write(self.style.SUCCESS('recalcular_comisiones_historicas completado exitosamente.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al ejecutar recalcular_comisiones_historicas: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('2. Ejecutando calcular_ganancias_historicas...'))
        try:
            call_command('calcular_ganancias_historicas')
            self.stdout.write(self.style.SUCCESS('calcular_ganancias_historicas completado exitosamente.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al ejecutar calcular_ganancias_historicas: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('Proceso de actualización completa de ganancias finalizado.'))
