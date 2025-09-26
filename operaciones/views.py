# operaciones/views.py

import decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from transacciones.models import Transaccion
from cotizaciones.models import Cotizacion
from pagos.services import ejecutar_acreditacion_a_cliente

def obtener_tasa_de_cambio_actual(moneda_origen, moneda_destino):
    """
    Obtiene la tasa de cambio más reciente para un par de monedas.
    Devuelve la tasa de 'compra' desde la perspectiva de la casa de cambio.
    """
    try:
        cotizacion = Cotizacion.objects.get(
            moneda_base=moneda_origen,
            moneda_destino=moneda_destino
        )
        return cotizacion.valor_compra
    except Cotizacion.DoesNotExist:
        return None

@csrf_exempt
@require_POST
def api_confirmar_deposito_tauser(request):
    """
    Endpoint para que el Tauser confirme el depósito de una transacción.
    Implementa el modelo híbrido:
    1. Verifica si la tasa garantizada está vigente (camino feliz).
    2. Si expiró, activa el fallback para confirmar la nueva tasa.
    """
    codigo_operacion = request.POST.get('codigo_operacion')
    if not codigo_operacion:
        return JsonResponse({'status': 'error', 'mensaje': 'El código de operación es requerido.'}, status=400)

    transaccion = get_object_or_404(Transaccion, codigo_operacion_tauser=codigo_operacion, estado='pendiente_deposito_tauser')

    # --- Verificación Proactiva de Expiración de Tasa ---
    if transaccion.is_tasa_expirada:
        transaccion.estado = 'cancelada_tasa_expirada'
        transaccion.save()
        return JsonResponse({
            'status': 'error',
            'mensaje': 'La operación no puede continuar porque la tasa garantizada ha expirado. La transacción ha sido cancelada.'
        }, status=400)

    # --- Lógica Central del Modelo Híbrido ---
    
    # 1. CAMINO FELIZ: Verificar si la garantía de la tasa sigue vigente.
    if transaccion.modalidad_tasa == 'bloqueada' and transaccion.tasa_garantizada_hasta and timezone.now() <= transaccion.tasa_garantizada_hasta:
        transaccion.estado = 'procesando_acreditacion'
        transaccion.save()
        
        # Llamar al servicio de pagos para iniciar la acreditación
        ejecutar_acreditacion_a_cliente(transaccion)
        
        return JsonResponse({'status': 'ok', 'mensaje': 'Operación confirmada. Tasa garantizada respetada.'})

    # 2. FALLBACK (GEG-105): La garantía expiró o no existía.
    tasa_actual = obtener_tasa_de_cambio_actual(transaccion.moneda_origen, transaccion.moneda_destino)

    if tasa_actual is None:
        return JsonResponse({'status': 'error', 'mensaje': 'No se pudo obtener la tasa de cambio actual.'}, status=500)

    # Si la tasa expiró pero casualmente es la misma, procedemos.
    if tasa_actual == transaccion.tasa_cambio_aplicada:
        transaccion.estado = 'procesando_acreditacion'
        transaccion.save()
        ejecutar_acreditacion_a_cliente(transaccion)
        return JsonResponse({'status': 'ok', 'mensaje': 'Operación confirmada. Tasa expirada pero sin cambios.'})
    
    # ¡La tasa es diferente! Debemos pedir confirmación al cliente en el Tauser.
    monto_nuevo = transaccion.monto_origen * tasa_actual
    
    return JsonResponse({
        'status': 'requiere_confirmacion',
        'mensaje': 'La tasa garantizada ha expirado y el valor ha cambiado. Por favor, pida al cliente que confirme para continuar.',
        'tasa_original': str(transaccion.tasa_cambio_aplicada),
        'tasa_nueva': str(tasa_actual),
        'monto_nuevo': str(monto_nuevo.quantize(decimal.Decimal('0.01')))
    })

@csrf_exempt
@require_POST
def api_resolver_variacion_tasa(request):
    """
    Endpoint para que el Tauser registre la decisión del cliente
    cuando la tasa de cambio ha variado y la garantía ha expirado.
    """
    codigo_operacion = request.POST.get('codigo_operacion')
    decision_cliente = request.POST.get('decision') # 'aceptar' o 'cancelar'

    if not all([codigo_operacion, decision_cliente]):
        return JsonResponse({'status': 'error', 'mensaje': 'Faltan parámetros requeridos.'}, status=400)

    transaccion = get_object_or_404(Transaccion, codigo_operacion_tauser=codigo_operacion)

    if decision_cliente == 'aceptar':
        tasa_nueva_str = request.POST.get('tasa_nueva')
        if not tasa_nueva_str:
            return JsonResponse({'status': 'error', 'mensaje': 'La nueva tasa es requerida para aceptar.'}, status=400)
        
        try:
            tasa_nueva = decimal.Decimal(tasa_nueva_str)
        except decimal.InvalidOperation:
            return JsonResponse({'status': 'error', 'mensaje': 'Formato de tasa inválido.'}, status=400)

        # El cliente aceptó la nueva tasa. Actualizamos y procedemos.
        transaccion.tasa_cambio_aplicada = tasa_nueva
        transaccion.monto_destino = transaccion.monto_origen * tasa_nueva
        transaccion.estado = 'procesando_acreditacion'
        transaccion.save()

        # Iniciar la acreditación con la nueva tasa
        ejecutar_acreditacion_a_cliente(transaccion)
        
        return JsonResponse({'status': 'ok', 'mensaje': 'Operación confirmada con la nueva tasa.'})

    elif decision_cliente == 'cancelar':
        # El cliente canceló. Marcamos la transacción.
        transaccion.estado = 'cancelada_usuario_tasa'
        transaccion.save()
        
        return JsonResponse({'status': 'cancelada', 'mensaje': 'Operación cancelada. Por favor, devuelva el dinero al cliente.'})
    
    else:
        return JsonResponse({'status': 'error', 'mensaje': 'Decisión no válida.'}, status=400)
