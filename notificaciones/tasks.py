# notificaciones/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from transacciones.models import Transaccion
from cotizaciones.models import Cotizacion
from django.db.models import Q
from .emails import enviar_email_cambio_tasa
from django.utils import timezone
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
        
    ]

    # 2. Construir el filtro base para transacciones pendientes de la moneda afectada
    moneda_extranjera = cotizacion.moneda_destino
    ahora = timezone.now()

    filtro_base = (
        Q(estado__in=estados_pendientes) &
        (Q(moneda_origen=moneda_extranjera) | Q(moneda_destino=moneda_extranjera)) &
        # EXCLUIR transacciones cuya tasa garantizada ya expiró.
        # Una transacción es válida para notificar SÓLO SI su garantía de tasa no ha expirado.
        (Q(tasa_garantizada_hasta__isnull=True) | Q(tasa_garantizada_hasta__gte=ahora))
    )

    transacciones_a_notificar = []

    # 3. Filtrar por tipo de operación y si la tasa realmente cambió
    if compra_cambio:
        # La empresa COMPRA divisa (cliente vende). Notificar si la tasa de compra cambió.
        # - Tasa bloqueada: si la tasa guardada es diferente a la nueva.
        # - Tasa flotante: siempre se notifica si la tasa de compra cambió.
        trans_bloqueadas_compra = Transaccion.objects.filter(filtro_base, tipo_operacion='compra', modalidad_tasa='bloqueada').exclude(tasa_cambio_aplicada=cotizacion.valor_compra)
        trans_flotantes_compra = Transaccion.objects.filter(filtro_base, tipo_operacion='compra', modalidad_tasa='flotante')
        
        transacciones_a_notificar.extend(list(trans_bloqueadas_compra))
        transacciones_a_notificar.extend(list(trans_flotantes_compra))

    if venta_cambio:
        # La empresa VENDE divisa (cliente compra). Notificar si la tasa de venta cambió.
        # - Tasa bloqueada: si la tasa guardada es diferente a la nueva.
        # - Tasa flotante: siempre se notifica si la tasa de venta cambió.
        trans_bloqueadas_venta = Transaccion.objects.filter(filtro_base, tipo_operacion='venta', modalidad_tasa='bloqueada').exclude(tasa_cambio_aplicada=cotizacion.valor_venta)
        trans_flotantes_venta = Transaccion.objects.filter(filtro_base, tipo_operacion='venta', modalidad_tasa='flotante')

        transacciones_a_notificar.extend(list(trans_bloqueadas_venta))
        transacciones_a_notificar.extend(list(trans_flotantes_venta))

    # 4. Obtener una lista única de usuarios a notificar
    # Usamos un set para evitar enviar múltiples correos al mismo usuario si tiene varias transacciones pendientes
    usuarios_a_notificar = set() # Usamos un set para evitar duplicados
    User = get_user_model()

    for t in transacciones_a_notificar:
        usuario = None
        # Lógica robusta para obtener el usuario, compatible con modelos antiguos y nuevos
        if hasattr(t, 'usuario_operador'):
            # Estructura nueva: el usuario está en `usuario_operador`
            usuario = t.usuario_operador
        elif isinstance(t.cliente, User):
            # Estructura antigua: el usuario estaba directamente en el campo `cliente`
            usuario = t.cliente
        
        if usuario:
            usuarios_a_notificar.add(usuario)

    if not usuarios_a_notificar:
        return "No se encontraron usuarios con transacciones pendientes para notificar."

    # 5. Iterar sobre los usuarios únicos y enviar notificaciones/emails
    for usuario in usuarios_a_notificar:
        # Obtener las preferencias del usuario
        preferencias = getattr(usuario, 'preferencias_notificacion', None)

        # --- Lógica de Preferencias de Moneda ---
        # Si el usuario tiene preferencias definidas y no sigue esta moneda, saltar.
        if preferencias and preferencias.monedas_seguidas.exists():
            if not preferencias.monedas_seguidas.filter(pk=cotizacion.moneda_destino.pk).exists():
                continue  # El usuario no quiere notificaciones para esta moneda.

        # Crear la notificación en el panel del usuario (esto es rápido)
        Notificacion.objects.create(
            destinatario=usuario,
            mensaje=mensaje,
        )

        # --- Lógica de Preferencias de Canal (Email) ---
        quiere_recibir_email = True
        if preferencias:
            quiere_recibir_email = preferencias.recibir_email_tasa_cambio

        if quiere_recibir_email:
            enviar_email_cambio_tasa(usuario, mensaje, cotizacion, venta_cambio, compra_cambio)

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
