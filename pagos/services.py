# pagos/services.py
import importlib
from django.http import HttpRequest
from django.utils import timezone # Importar timezone
from datetime import timedelta # Importar timedelta
from django.urls import reverse # Importar reverse para construir URLs
from urllib.parse import urlencode # Importar urlencode para construir parámetros de URL
from .models import TipoMedioPago
from transacciones.models import Transaccion
from payments.stripe_service import create_payment_intent # Importar el servicio de Stripe

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

    # Lógica específica para Stripe
    if engine_name == 'stripe':
        try:
            # Convertir el monto a centavos, asumiendo que la moneda de origen es USD para Stripe
            # (o la moneda configurada para Stripe en la transacción)
            # Aquí asumimos que transaccion.monto_origen es la cantidad en USD que el cliente va a pagar
            # y que transaccion.moneda_origen.codigo es 'USD'.
            # Si el cliente está comprando USD, paga con PYG. Si vende USD, recibe PYG.
            # La integración de Stripe es para cuando el cliente PAGA con USD (es decir, la casa de cambio COMPRA USD).
            # Por lo tanto, el monto_origen de la transacción es el USD que el cliente está pagando.
            amount_in_cents = int(transaccion.monto_origen * 100)
            currency = transaccion.moneda_origen.codigo.lower() # 'usd'

            payment_intent_data = create_payment_intent(
                amount_in_cents=amount_in_cents,
                currency=currency,
                customer_email=request.user.email,
                transaction_id=str(transaccion.id) # ¡ESTA ES LA LÍNEA CRUCIAL QUE TE FALTABA!
            )

            client_secret = payment_intent_data.get('clientSecret')
            if not client_secret:
                raise Exception(f"No se pudo obtener el client_secret de Stripe: {payment_intent_data.get('error', 'Error desconocido')}")

            base_url = reverse('payments:stripe_payment_page')
            params = urlencode({
                'client_secret': client_secret,
                'transaction_id': str(transaccion.id),
            })
            redirect_url = f'{base_url}?{params}'
            print(f"INFO: [PAGOS] Redirigiendo a Stripe para transacción {transaccion.id}: {redirect_url}")
            return redirect_url

        except Exception as e:
            print(f"ERROR: [PAGOS] Error al iniciar pago con Stripe para transacción {transaccion.id}: {e}")
            return None
    
    # Lógica para otros gateways (existente)
    gateway_module_name = f"pagos.gateways.{engine_name}_gateway"

    # 2. Cargar dinámicamente el módulo del gateway
    try:
        gateway_module = importlib.import_module(gateway_module_name)
        print(f"INFO: [PAGOS] Cargando gateway: {gateway_module_name}")
    except ImportError:
        print(f"ERROR: [PAGOS] No se pudo encontrar el módulo de gateway: {gateway_module_name}")
        return None

    # 3. Delegar la ejecución al gateway
    try:
        # Asumimos que la clase del gateway se llama igual que el engine pero con CamelCase
        gateway_class_name = f"{engine_name.capitalize()}Gateway"
        gateway_class = getattr(gateway_module, gateway_class_name)
        
        gateway_instance = gateway_class()
        return gateway_instance.initiate_payment(transaccion, request)
    except AttributeError:
        print(f"ERROR: [PAGOS] La clase '{gateway_class_name}' o el método 'initiate_payment' no está definido en {gateway_module_name}")
        return None
    except Exception as e:
        print(f"ERROR: [PAGOS] Error al iniciar pago con gateway {engine_name}: {e}")
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

def handle_payment_webhook(payload: dict):
    """
    Orquestador de webhooks para procesar notificaciones de pasarelas de pago.

    Esta función determina qué pasarela de pago manejó el webhook
    y delega el procesamiento al gateway específico.

    Args:
        payload (dict): El payload del webhook recibido de la pasarela.

    Returns:
        dict: Un diccionario con el resultado del procesamiento del webhook.
    """
    # --- ESTA ES LA LÓGICA CORREGIDA PARA WEBHOOKS ---
    event_type = payload.get('type')
    data_object = payload.get('data', {}).get('object', {})
    
    # 1. Obten el objeto del evento (ej: un PaymentIntent)
    # Asumimos que el payload ya es el resultado de event.to_dict()
    payment_intent = data_object 

    # 2. Busca tu ID de transacción. Primero intenta con el formato Stripe (metadata),
    # luego con el formato de pasarelas locales (referencia_comercio directa).
    transaccion_id = None
    if data_object and data_object.get('metadata'):
        transaccion_id = data_object['metadata'].get('transaccion_id')
        if not transaccion_id:
            transaccion_id = data_object['metadata'].get('transaction_id') # Por si acaso se usó la clave antigua

    # Si no se encontró en metadata, intentar buscar en el payload principal (para pasarelas locales)
    if not transaccion_id:
        transaccion_id = payload.get('referencia_comercio')
    
    # 3. Valida
    if not transaccion_id:
        print("ERROR: [PAGOS WEBHOOK] Error: El webhook no contenía un ID de transacción válido (ni en metadata ni como referencia_comercio).")
        return {'status': 'ERROR', 'message': 'Webhook no contenía un ID de transacción válido.'}

    try:
        transaccion = Transaccion.objects.get(id=transaccion_id)
        medio_pago = transaccion.medio_pago_utilizado
    except Transaccion.DoesNotExist:
        print(f"ERROR: [PAGOS WEBHOOK] Transacción {transaccion_id} no encontrada.")
        return {'status': 'ERROR', 'message': 'Transacción no encontrada.'}
    except AttributeError:
        print(f"ERROR: [PAGOS WEBHOOK] Transacción {transaccion_id} no tiene medio de pago asociado.")
        return {'status': 'ERROR', 'message': 'Medio de pago no asociado.'}

    if not medio_pago or not medio_pago.activo or medio_pago.engine == 'manual':
        print(f"ERROR: [PAGOS WEBHOOK] Medio de pago '{medio_pago.nombre if medio_pago else 'N/A'}' no válido para webhook.")
        return {'status': 'ERROR', 'message': 'Medio de pago no válido.'}

    engine_name = medio_pago.engine

    # Lógica específica para Stripe Webhook
    if engine_name == 'stripe':
        # Aquí ya no delegamos a payments.stripe_service.handle_webhook
        # porque la lógica de procesamiento se mueve aquí.
        if event_type == 'payment_intent.succeeded':
            try:
                transaccion.estado = 'pendiente_retiro_tauser' # O 'completada'
                transaccion.save(update_fields=['estado'])
                print(f"INFO: [STRIPE WEBHOOK] Éxito: Transacción {transaccion_id} completada.")
                return {'status': 'EXITOSO', 'message': 'Pago exitoso y transacción actualizada.'}
            except Exception as e:
                print(f"ERROR: [STRIPE WEBHOOK] Error al actualizar transacción {transaccion_id}: {e}")
                return {'status': 'ERROR', 'message': f'Error al actualizar transacción: {e}'}
        elif event_type == 'payment_intent.payment_failed':
            transaccion.estado = 'cancelada'
            transaccion.save(update_fields=['estado'])
            print(f"INFO: [STRIPE WEBHOOK] Transacción {transaccion_id} actualizada a 'cancelada' por fallo de pago.")
            return {'status': 'RECHAZADO', 'message': 'Pago fallido y transacción cancelada.'}
        else:
            print(f"INFO: [STRIPE WEBHOOK] Evento de Stripe {event_type} no manejado explícitamente para Transacción {transaccion_id}.")
            return {'status': 'IGNORADO', 'message': f'Evento {event_type} no manejado.'}

    # Lógica para otros gateways (existente)
    gateway_module_name = f"pagos.gateways.{engine_name}_gateway"

    try:
        gateway_module = importlib.import_module(gateway_module_name)
        gateway_class_name = f"{engine_name.capitalize()}Gateway"
        gateway_class = getattr(gateway_module, gateway_class_name)
        
        gateway_instance = gateway_class()
        webhook_result = gateway_instance.handle_webhook(payload)

        # Lógica de validación de tasa garantizada para Flujo A
        if transaccion.modalidad_tasa == 'bloqueada' and transaccion.estado == 'pendiente_pago_cliente':
            if transaccion.is_tasa_expirada:
                transaccion.estado = 'cancelada_tasa_expirada'
                transaccion.save(update_fields=['estado'])
                print(f"WARN: [PAGOS WEBHOOK] Transacción {transaccion.id} cancelada por tasa expirada. Se requiere reembolso.")
                return {'status': 'ERROR', 'message': 'Tasa garantizada expirada. Pago recibido fuera de tiempo.'}
            
        # Actualizar el estado de la transacción basándose en el resultado del gateway
        if webhook_result.get('status') == 'EXITOSO':
            if transaccion.estado == 'pendiente_pago_cliente':
                transaccion.estado = 'pendiente_retiro_tauser'
                transaccion.save(update_fields=['estado'])
                print(f"INFO: [PAGOS WEBHOOK] Transacción {transaccion.id} actualizada a 'pendiente_retiro_tauser'.")
            else:
                print(f"WARN: [PAGOS WEBHOOK] Transacción {transaccion.id} ya no estaba pendiente de pago. Estado actual: {transaccion.estado}")
        elif webhook_result.get('status') == 'RECHAZADO':
            if transaccion.estado == 'pendiente_pago_cliente':
                transaccion.estado = 'cancelada'
                transaccion.save(update_fields=['estado'])
                print(f"INFO: [PAGOS WEBHOOK] Transacción {transaccion.id} actualizada a 'cancelada'.")
            else:
                print(f"WARN: [PAGOS WEBHOOK] Transacción {transaccion.id} ya no estaba pendiente de pago. Estado actual: {transaccion.estado}")
        
        return webhook_result # Devolver el resultado original del gateway
    except ImportError:
        print(f"ERROR: [PAGOS WEBHOOK] No se pudo encontrar el módulo de gateway: {gateway_module_name}")
        return {'status': 'ERROR', 'message': 'Gateway no encontrado.'}
    except AttributeError:
        print(f"ERROR: [PAGOS WEBHOOK] La clase '{gateway_class_name}' o el método 'handle_webhook' no está definido en {gateway_module_name}")
        return {'status': 'ERROR', 'message': 'Método de webhook no implementado.'}
    except Exception as e:
        print(f"ERROR: [PAGOS WEBHOOK] Error al manejar webhook con gateway {engine_name}: {e}")
        return {'status': 'ERROR', 'message': f'Error interno: {e}'}
