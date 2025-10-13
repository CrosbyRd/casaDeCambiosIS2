# notificaciones/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from transacciones.models import Transaccion
from cotizaciones.models import Cotizacion
from django.db.models import Q
from .emails import enviar_email_cambio_tasa
from .models import Notificacion

@shared_task
def notificar_cambio_de_tasa_a_usuarios(cotizacion_id, mensaje, compra_cambio, venta_cambio):
    """
    Tarea de Celery para enviar notificaciones de cambio de tasa en segundo plano.

    MODIFICADO: Ahora solo notifica a clientes con transacciones pendientes.
    """
    try:
        cotizacion = Cotizacion.objects.get(pk=cotizacion_id)
    except Cotizacion.DoesNotExist:
        return "Cotización no encontrada. No se enviaron notificaciones."

    # 1. Definir los estados de transacción que consideramos "pendientes"
    estados_pendientes = [
        'pendiente_pago_cliente',
        'pendiente_retiro_tauser',
        'pendiente_deposito_tauser',
        'procesando_acreditacion',
    ]

    # 2. Construir el filtro base para transacciones pendientes de la moneda afectada
    moneda_extranjera = cotizacion.moneda_destino
    filtro_base = Q(estado__in=estados_pendientes) & (
        Q(moneda_origen=moneda_extranjera) | Q(moneda_destino=moneda_extranjera)
    )

    transacciones_a_notificar = []

    # 3. Filtrar por tipo de operación y si la tasa realmente cambió
    if compra_cambio:
        # La empresa COMPRA divisa (cliente vende). Notificar si la tasa de compra cambió.
        transacciones_compra = Transaccion.objects.filter(
            filtro_base,
            tipo_operacion='compra'
        ).exclude(tasa_cambio_aplicada=cotizacion.valor_compra)
        transacciones_a_notificar.extend(list(transacciones_compra))

    if venta_cambio:
        # La empresa VENDE divisa (cliente compra). Notificar si la tasa de venta cambió.
        transacciones_venta = Transaccion.objects.filter(
            filtro_base,
            tipo_operacion='venta'
        ).exclude(tasa_cambio_aplicada=cotizacion.valor_venta)
        transacciones_a_notificar.extend(list(transacciones_venta))

    # 4. Obtener una lista única de usuarios a notificar
    # Usamos un set para evitar enviar múltiples correos al mismo usuario si tiene varias transacciones pendientes
    usuarios_a_notificar = {t.usuario_operador for t in transacciones_a_notificar}

    if not usuarios_a_notificar:
        return "No se encontraron usuarios con transacciones pendientes para notificar."

    # 4. Iterar sobre los usuarios únicos y enviar notificaciones/emails
    for usuario in usuarios_a_notificar:
        # Crear la notificación en el panel del usuario (esto es rápido)
        Notificacion.objects.create(
            destinatario=usuario,
            mensaje=mensaje,
        )

        # Comprobar preferencias de email y enviar
        quiere_recibir_email = True
        preferencias = getattr(usuario, 'preferencias_notificacion', None)
        if preferencias:
            quiere_recibir_email = preferencias.recibir_email_tasa_cambio

        if quiere_recibir_email:
            enviar_email_cambio_tasa(usuario, mensaje, cotizacion)

    return f"Notificaciones enviadas a {len(usuarios_a_notificar)} usuarios con transacciones pendientes."





# # /home/richar-carballo/Escritorio/IS2/casaDeCambiosIS2/notificaciones/tasks.py (NUEVO ARCHIVO)
# from celery import shared_task
# from django.contrib.auth import get_user_model
# from .emails import enviar_email_cambio_tasa
# from .models import Notificacion
# from cotizaciones.models import Cotizacion

# @shared_task
# def notificar_cambio_de_tasa_a_usuarios(cotizacion_id, mensaje):
#     """
#     Tarea de Celery para enviar notificaciones de cambio de tasa en segundo plano.
#     """
#     try:
#         cotizacion = Cotizacion.objects.get(pk=cotizacion_id)
#     except Cotizacion.DoesNotExist:
#         # Si la cotización fue eliminada, no hacemos nada.
#         return

#     User = get_user_model()
#     usuarios_a_notificar = User.objects.filter(is_active=True)

#     for usuario in usuarios_a_notificar:
#         # 1. Crear la notificación en el panel (esto es rápido)
#         Notificacion.objects.create(
#             destinatario=usuario,
#             mensaje=mensaje,
#         )

#         # 2. Comprobar preferencias y enviar email (esto es lo que queremos en segundo plano)
#         quiere_recibir_email = True
#         preferencias = getattr(usuario, 'preferencias_notificacion', None)
#         if preferencias:
#             quiere_recibir_email = preferencias.recibir_email_tasa_cambio

#         if quiere_recibir_email:
#             enviar_email_cambio_tasa(usuario, mensaje, cotizacion)

#     return f"Notificaciones enviadas para la cotización {cotizacion_id} a {usuarios_a_notificar.count()} usuarios."
