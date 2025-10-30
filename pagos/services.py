# pagos/services.py
import importlib
from django.http import HttpRequest
from django.utils import timezone  # Importar timezone (si lo usas en otra parte)
from datetime import timedelta      # Importar timedelta (si lo usas en otra parte)
from django.urls import reverse     # Importar reverse para construir URLs
from urllib.parse import urlencode  # Importar urlencode para construir parámetros de URL
from .models import TipoMedioPago
from transacciones.models import Transaccion
from payments.stripe_service import create_payment_intent  # Servicio de Stripe

# >>> Integración con facturación electrónica (imports mínimos y seguros)
from facturacion_electronica.tasks import generar_factura_electronica_task
from facturacion_electronica.models import EmisorFacturaElectronica, DocumentoElectronico

import uuid  # Necesario si simulas o generas ids en otros flujos


def iniciar_cobro_a_cliente(transaccion: Transaccion, request: HttpRequest, medio_pago_id: str):
    """
    Orquestador de pagos para iniciar un cobro a un cliente.

    1) Determina el gateway a usar según el medio de pago.
    2) Carga dinámicamente el módulo del gateway.
    3) Delega la ejecución al gateway correspondiente.

    Devuelve URL de redirección o None si falla.
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
            # Monto en centavos y moneda; aquí asumimos monto_origen y moneda_origen
            amount_in_cents = int(transaccion.monto_origen * 100)
            currency = transaccion.moneda_origen.codigo.lower()  # 'usd', etc.

            payment_intent_data = create_payment_intent(
                amount_in_cents=amount_in_cents,
                currency=currency,
                customer_email=request.user.email,
                transaction_id=str(transaccion.id)  # clave para recuperar la transacción en el webhook
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
    (Flujo de VENTA de divisas del cliente; no se modifica)
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
    Orquestador de webhooks de pago.

    Determina la pasarela, procesa el evento y actualiza la Transaccion.
    Si el pago es exitoso, dispara la emisión de la factura electrónica (idempotente).
    """
    event_type = payload.get('type')
    data_object = payload.get('data', {}).get('object', {})

    # 1) localizar transaccion_id (Stripe metadata o pasarelas locales)
    transaccion_id = None
    if data_object and data_object.get('metadata'):
        transaccion_id = data_object['metadata'].get('transaccion_id') or data_object['metadata'].get('transaction_id')

    if not transaccion_id:
        transaccion_id = payload.get('referencia_comercio')

    if not transaccion_id:
        print("ERROR: [PAGOS WEBHOOK] Webhook sin ID de transacción válido.")
        return {'status': 'ERROR', 'message': 'Webhook sin transaccion_id.'}

    # 2) obtener transacción y medio
    try:
        transaccion = Transaccion.objects.get(id=transaccion_id)
        medio_pago = transaccion.medio_pago_utilizado
    except Transaccion.DoesNotExist:
        print(f"ERROR: [PAGOS WEBHOOK] Transacción {transaccion_id} no encontrada.")
        return {'status': 'ERROR', 'message': 'Transacción no encontrada.'}
    except AttributeError:
        print(f"ERROR: [PAGOS WEBHOOK] Transacción {transaccion_id} sin medio de pago asociado.")
        return {'status': 'ERROR', 'message': 'Medio de pago no asociado.'}

    if not medio_pago or not medio_pago.activo or medio_pago.engine == 'manual':
        print(f"ERROR: [PAGOS WEBHOOK] Medio de pago inválido: {getattr(medio_pago, 'nombre', 'N/A')}")
        return {'status': 'ERROR', 'message': 'Medio de pago no válido.'}

    engine_name = medio_pago.engine

    # 3) STRIPE: procesa localmente el intent
    if engine_name == 'stripe':
        if event_type == 'payment_intent.succeeded':
            try:
                # Actualiza estado de transacción (mantengo tu lógica)
                if transaccion.estado == 'pendiente_pago_cliente':
                    transaccion.estado = 'pendiente_retiro_tauser'  # o 'completada' si tu flujo lo requiere
                    transaccion.save(update_fields=['estado'])
                print(f"INFO: [STRIPE WEBHOOK] Éxito: Transacción {transaccion_id} actualizada.")

                # --- Disparo idempotente de facturación electrónica ---
                _emitir_factura_si_corresponde(transaccion)
                return {'status': 'EXITOSO', 'message': 'Pago exitoso y transacción actualizada.'}
            except Exception as e:
                print(f"ERROR: [STRIPE WEBHOOK] Error al actualizar Tx {transaccion_id} o emitir factura: {e}")
                return {'status': 'ERROR', 'message': f'Error al procesar: {e}'}

        elif event_type == 'payment_intent.payment_failed':
            if transaccion.estado == 'pendiente_pago_cliente':
                transaccion.estado = 'cancelada'
                transaccion.save(update_fields=['estado'])
            print(f"INFO: [STRIPE WEBHOOK] Tx {transaccion_id} marcada cancelada por fallo de pago.")
            return {'status': 'RECHAZADO', 'message': 'Pago fallido y transacción cancelada.'}

        print(f"INFO: [STRIPE WEBHOOK] Evento no manejado: {event_type} para Tx {transaccion_id}.")
        return {'status': 'IGNORADO', 'message': f'Evento {event_type} no manejado.'}

    # 4) Otros gateways: delega a su handler y actúa según resultado
    gateway_module_name = f"pagos.gateways.{engine_name}_gateway"
    try:
        gateway_module = importlib.import_module(gateway_module_name)
        gateway_class_name = f"{engine_name.capitalize()}Gateway"
        gateway_class = getattr(gateway_module, gateway_class_name)
        gateway_instance = gateway_class()
        webhook_result = gateway_instance.handle_webhook(payload)

        # Validar expiración de tasa garantizada si aplica
        if transaccion.modalidad_tasa == 'bloqueada' and transaccion.estado == 'pendiente_pago_cliente' and getattr(transaccion, "is_tasa_expirada", False):
            transaccion.estado = 'cancelada_tasa_expirada'
            transaccion.save(update_fields=['estado'])
            print(f"WARN: [PAGOS WEBHOOK] Tx {transaccion.id} cancelada por tasa expirada. Revisar reembolso.")
            return {'status': 'ERROR', 'message': 'Tasa garantizada expirada. Pago fuera de tiempo.'}

        if webhook_result.get('status') == 'EXITOSO':
            if transaccion.estado == 'pendiente_pago_cliente':
                transaccion.estado = 'pendiente_retiro_tauser'
                transaccion.save(update_fields=['estado'])
                print(f"INFO: [PAGOS WEBHOOK] Tx {transaccion.id} -> 'pendiente_retiro_tauser'.")

                # --- Disparo idempotente de facturación electrónica ---
                _emitir_factura_si_corresponde(transaccion)

        elif webhook_result.get('status') == 'RECHAZADO':
            if transaccion.estado == 'pendiente_pago_cliente':
                transaccion.estado = 'cancelada'
                transaccion.save(update_fields=['estado'])
                print(f"INFO: [PAGOS WEBHOOK] Tx {transaccion.id} -> 'cancelada'.")

        return webhook_result

    except ImportError:
        print(f"ERROR: [PAGOS WEBHOOK] Módulo gateway no encontrado: {gateway_module_name}")
        return {'status': 'ERROR', 'message': 'Gateway no encontrado.'}
    except AttributeError:
        print(f"ERROR: [PAGOS WEBHOOK] Clase/método no encontrado en {gateway_module_name}")
        return {'status': 'ERROR', 'message': 'Webhook no implementado en gateway.'}
    except Exception as e:
        print(f"ERROR: [PAGOS WEBHOOK] Error interno con gateway {engine_name}: {e}")
        return {'status': 'ERROR', 'message': f'Error interno: {e}'}


def _emitir_factura_si_corresponde(transaccion: Transaccion):
    """
    Emite la factura electrónica de forma idempotente:
    - Requiere un Emisor ACTIVO.
    - No emite si ya existe un DocumentoElectronico no finalizado con esta transacción.
    - Delega el armado del DE y numeración a la task de facturación.
    """
    try:
        existe = DocumentoElectronico.objects.filter(
            transaccion_asociada=transaccion
        ).exclude(
            estado_sifen__in=['rechazado', 'inutilizado', 'error_api', 'error_sifen']
        ).exists()

        if existe:
            print(f"INFO: [FACTURACION] Ya existe documento para Tx {transaccion.id}; no se dispara nuevamente.")
            return

        emisor = EmisorFacturaElectronica.objects.filter(activo=True).first()
        if not emisor:
            print("WARN: [FACTURACION] No hay Emisor ACTIVO configurado. No se emite factura.")
            return

        receptor_email = getattr(getattr(transaccion, "cliente", None), "email", "receptor@test.com")

        # Llamamos a la task usando kwargs para evitar problemas de aridad en Celery
        generar_factura_electronica_task.delay(
            emisor_id=str(emisor.id),
            transaccion_id=str(transaccion.id),
            json_de_completo=None,             # el builder de la task arma el DE a partir de la Transaccion
            email_receptor=receptor_email
        )
        print(f"INFO: [FACTURACION] Task disparada para Tx {transaccion.id} con Emisor {emisor.id}.")

    except Exception as e:
        print(f"ERROR: [FACTURACION] No se pudo disparar la emisión para Tx {transaccion.id}: {e}")


def build_json_de_from_transaction(transaccion: Transaccion, emisor: EmisorFacturaElectronica) -> dict:
    """
    (Conservado por compatibilidad) Construye un JSON de DE a partir de una transacción.
    Nota: Actualmente NO se usa en el flujo principal; la task de facturación arma el DE.
    Puedes usarlo para diagnósticos o pruebas puntuales.
    """
    cliente = transaccion.cliente

    json_de_completo = {
        "dDV": emisor.dv_ruc,
        "dRucEm": emisor.ruc,
        "dNomEm": emisor.nombre,
        "dDirEm": emisor.direccion,
        "dNumCas": emisor.numero_casa,
        "dDesCiu": emisor.descripcion_ciudad,
        "cUniMed": "77",
        "dDesDep": emisor.descripcion_departamento,
        "cDep": emisor.codigo_departamento,
        "dTelEm": emisor.telefono,
        "dEmailEm": emisor.email_emisor,
        "dActEco": emisor.actividades_economicas,
        "dEst": emisor.establecimiento,
        "dPunExp": emisor.punto_expedicion,
        "dNumTim": emisor.numero_timbrado_actual,
        "dNumDoc": str(emisor.siguiente_numero_factura).zfill(7),
        "iTiDE": "1",
        "dFeEmi": timezone.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "dTotOpe": str(transaccion.monto_origen),
        "dMoneda": transaccion.moneda_origen.codigo,
        "dTipCam": str(transaccion.tasa_cambio_aplicada),
        "dNomRec": cliente.get_full_name(),
        "dRucRec": getattr(cliente, 'ruc', ''),
        "dDirRec": getattr(cliente, 'direccion', ''),
        "dTelRec": getattr(cliente, 'telefono', ''),
        "dEmailRec": getattr(cliente, 'email', ''),
        "items": [
            {
                "dDesProSer": f"Cambio de {transaccion.monto_origen} {transaccion.moneda_origen.codigo} a {transaccion.monto_destino} {transaccion.moneda_destino.codigo}",
                "dCantProSer": "1",
                "dUniMed": "UNI",
                "dPrUnit": str(transaccion.monto_origen),
                "dTotOpeItem": str(transaccion.monto_origen),
                "dIVA": "0",
                "iAfecIVA": "1",
            }
        ]
    }

    if transaccion.tipo_operacion == 'compra':
        json_de_completo["dTotOpe"] = str(transaccion.monto_destino)
        json_de_completo["dMoneda"] = transaccion.moneda_destino.codigo
        json_de_completo["items"][0]["dDesProSer"] = (
            f"Compra de {transaccion.monto_origen} {transaccion.moneda_origen.codigo} "
            f"por {transaccion.monto_destino} {transaccion.moneda_destino.codigo}"
        )
        json_de_completo["items"][0]["dPrUnit"] = str(transaccion.monto_destino)
        json_de_completo["items"][0]["dTotOpeItem"] = str(transaccion.monto_destino)

    return json_de_completo
