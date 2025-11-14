from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone # Importar timezone
from transacciones.models import Transaccion
from monedas.models import Moneda
from decimal import Decimal # Importar Decimal para cálculos precisos
from .models import RegistroGanancia
# Ya no necesitamos importar Cotizacion ni Cliente aquí, ya que la comisión se toma directamente de la transacción.
# from cotizaciones.models import Cotizacion
# from clientes.models import Cliente

@receiver(post_save, sender=Transaccion)
def crear_o_actualizar_registro_ganancia(sender, instance, created, **kwargs):
    """
    Crea o actualiza un RegistroGanancia cuando una Transaccion se marca como 'completada'.
    """
    if instance.estado == 'completada':
        # Obtener la moneda PYG (asumiendo que es la moneda base)
        try:
            moneda_pyg = Moneda.objects.get(codigo="PYG")
        except Moneda.DoesNotExist:
            # Manejar el caso si PYG no existe, quizás loggear un error o usar un valor por defecto
            print("Error: Moneda PYG no encontrada. No se puede registrar la ganancia.")
            return

        # Determinar la moneda operada (la moneda extranjera de la transacción)
        moneda_operada = None
        
        if instance.tipo_operacion == 'venta':
            moneda_operada = instance.moneda_destino
        elif instance.tipo_operacion == 'compra':
            moneda_operada = instance.moneda_origen
        else:
            print(f"Advertencia: Tipo de operación desconocido '{instance.tipo_operacion}' para Transaccion {instance.id}. No se puede registrar la ganancia.")
            return

        # Usar la comision_cotizacion guardada en la transacción
        comision_bruta_registrada = instance.comision_cotizacion
        # instance.comision_aplicada ahora contiene la bonificación (descuento)
        bonificacion_monto = instance.comision_aplicada
        comision_final = comision_bruta_registrada - bonificacion_monto

        # Determinar el monto de la moneda operada para calcular la ganancia
        monto_operado_para_ganancia = Decimal('0.00')
        if instance.tipo_operacion == 'venta':
            # Si la empresa vende (cliente compra), la ganancia se calcula sobre el monto de la moneda destino (ej. USD)
            monto_operado_para_ganancia = instance.monto_destino
        elif instance.tipo_operacion == 'compra':
            # Si la empresa compra (cliente vende), la ganancia se calcula sobre el monto de la moneda origen (ej. USD)
            monto_operado_para_ganancia = instance.monto_origen
        
        ganancia_neta_real = comision_final * monto_operado_para_ganancia
    
        # Crear o actualizar el RegistroGanancia
        RegistroGanancia.objects.update_or_create(
            transaccion=instance,
            defaults={
                'ganancia_registrada': ganancia_neta_real,
                'moneda_ganancia': moneda_pyg,
                'moneda_operada': moneda_operada,
                'fecha_registro': timezone.now(),
            }
        )
        print(f"Registro de ganancia creado/actualizado para Transaccion {instance.id} con ganancia neta real: {ganancia_neta_real}")
