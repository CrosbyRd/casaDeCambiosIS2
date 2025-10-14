# pagos/services.py
import importlib
from django.http import HttpRequest
from .models import TipoMedioPago
from transacciones.models import Transaccion

def iniciar_cobro_a_cliente(transaccion: Transaccion, request: HttpRequest, medio_pago_id: str):
    """
    Orquestador de pagos para iniciar un cobro a un cliente.

    Esta función actúa como un orquestador:
    1. Determina qué pasarela de pago usar según el medio de pago.
    2. Carga dinámicamente el módulo del gateway correspondiente.
    3. Delega la ejecución al gateway específico.

    Args:
        transaccion (Transaccion): La instancia de la transacción a cobrar.
        request (HttpRequest): La petición original para construir URLs.
        medio_pago_id (str): El ID (UUID como string) del TipoMedioPago a utilizar.

    Returns:
        str: La URL de redirección a la pasarela de pago.
        None: Si ocurre un error.
    """
    # 1. Determinar el gateway a utilizar
    try:
        medio_pago = TipoMedioPago.objects.get(id_tipo=medio_pago_id)
    except TipoMedioPago.DoesNotExist:
        print(f"ERROR: [PAGOS] No se encontró el medio de pago con ID: {medio_pago_id}")
        return None

    if not medio_pago.activo or medio_pago.engine == 'manual':
        print(f"ERROR: [PAGOS] El medio de pago '{medio_pago.nombre}' no está activo o no es procesable automáticamente.")
        return None

    engine_name = medio_pago.engine
    gateway_module_name = f"pagos.gateways.{engine_name}_gateway"

    # 2. Cargar dinámicamente el módulo del gateway
    try:
        gateway_module = importlib.import_module(gateway_module_name)
        print(f"INFO: [PAGOS] Cargando gateway: {gateway_module_name}")
    except ImportError:
        print(f"ERROR: [PAGOS] No se pudo encontrar el módulo de gateway: {gateway_module_name}")
        return None

    # 3. Delegar la ejecución al gateway
    if hasattr(gateway_module, 'iniciar_pago'):
        return gateway_module.iniciar_pago(transaccion, request)
    else:
        print(f"ERROR: [PAGOS] La función 'iniciar_pago' no está definida en {gateway_module_name}")
        return None


def ejecutar_acreditacion_a_cliente(transaccion):
    """
    Simula la transferencia de dinero (PYG) a la cuenta del cliente.
    (Esta función es para el flujo de VENTA de divisas del cliente y no se ve afectada)
    """
    print("="*50)
    print(f"INFO: [SIMULACIÓN DE PAGO] Iniciando acreditación para la transacción {transaccion.id}.")
    print(f"INFO: -> Cliente: {transaccion.cliente.get_full_name()}")
    if transaccion.medio_acreditacion_cliente:
        print(f"INFO: -> Medio de Acreditación: {transaccion.medio_acreditacion_cliente.id}")
    else:
        print("WARN: -> No se especificó un medio de acreditación.")
    
    print(f"INFO: -> Monto a acreditar: {transaccion.monto_destino} {transaccion.moneda_destino.codigo}")
    print("="*50)
    
    return True
