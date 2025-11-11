from django.db.models.signals import post_save
from django.dispatch import receiver
from transacciones.models import Transaccion
from monedas.models import Moneda
from .models import RegistroGanancia

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
        if instance.tipo_operacion == 'venta':
            # Si la casa de cambio vende divisa al cliente, la moneda operada es la moneda destino
            moneda_operada = instance.moneda_destino
        elif instance.tipo_operacion == 'compra':
            # Si la casa de cambio compra divisa al cliente, la moneda operada es la moneda origen
            moneda_operada = instance.moneda_origen
        else:
            print(f"Advertencia: Tipo de operación desconocido '{instance.tipo_operacion}' para Transaccion {instance.id}. No se puede registrar la ganancia.")
            return

        # Crear o actualizar el RegistroGanancia
        RegistroGanancia.objects.update_or_create(
            transaccion=instance,
            defaults={
                'ganancia_registrada': instance.comision_aplicada,
                'moneda_ganancia': moneda_pyg,
                'moneda_operada': moneda_operada,
            }
        )
        print(f"Registro de ganancia creado/actualizado para Transaccion {instance.id}")
