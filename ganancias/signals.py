"""
Señales de la aplicación **ganancias**.

.. module:: ganancias.signals
   :synopsis: Cálculo y registro automático de ganancias a partir de transacciones.

Este módulo conecta la señal :data:`django.db.models.signals.post_save` del
modelo :class:`transacciones.models.Transaccion` con la lógica de negocio que
calcula y persiste instancias de :class:`ganancias.models.RegistroGanancia`.
"""


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
    Crea o actualiza un :class:`RegistroGanancia` cuando una transacción
    se marca como ``completada``.

    Lógica principal
    ----------------
    1. Verifica que ``instance.estado == 'completada'``.
    2. Obtiene la moneda PYG (moneda base en la que se registra la ganancia).
    3. Determina la moneda operada según el tipo de operación:

       - ``venta``: se toma ``instance.moneda_destino``.
       - ``compra``: se toma ``instance.moneda_origen``.

    4. Calcula la comisión final como::

           comision_final = comision_cotizacion - comision_aplicada

       donde ``comision_cotizacion`` es la comisión bruta de la cotización
       y ``comision_aplicada`` incluye eventuales bonificaciones.

    5. El monto operado para la ganancia depende del tipo de operación:

       - ``venta``: se usa ``instance.monto_destino``.
       - ``compra``: se usa ``instance.monto_origen``.

    6. Calcula la ganancia neta real como el producto de la comisión final
       por el monto operado y registra el resultado en
       :class:`RegistroGanancia` mediante :meth:`update_or_create`.

    :param sender: Modelo que dispara la señal (``Transaccion``).
    :type sender: type
    :param instance: Instancia de transacción recién guardada.
    :type instance: transacciones.models.Transaccion
    :param created: Indica si la instancia fue creada (``True``) o actualizada.
    :type created: bool
    :param kwargs: Parámetros adicionales de la señal (no utilizados).
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
        #print(f"Registro de ganancia creado/actualizado para Transaccion {instance.id} con ganancia neta real: {ganancia_neta_real}")
