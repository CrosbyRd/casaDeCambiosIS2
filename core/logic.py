"""
Módulo de lógica de negocio para cálculos de simulación de cambio de divisas.

Este módulo contiene la función principal para calcular simulaciones de compra y venta de divisas,
aplicando tasas, comisiones y bonificaciones de cliente.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from cotizaciones.models import Cotizacion
from monedas.models import Moneda
from django.core.exceptions import ObjectDoesNotExist
from ted.logic import ajustar_monto_a_denominaciones_disponibles

User = get_user_model()

def calcular_simulacion(monto_origen: Decimal, moneda_origen: str, moneda_destino: str, user: User = None) -> dict:
    """
    Calcula una simulación de cambio de divisas entre una moneda de origen y una de destino.

    La simulación considera la tasa de cambio, comisiones y posibles bonificaciones
    aplicables a un usuario autenticado. Las transacciones deben involucrar PYG
    como moneda base o destino.

    :param monto_origen: El monto de la moneda de origen a cambiar.
    :type monto_origen: Decimal
    :param moneda_origen: El código de la moneda de origen (ej. 'PYG', 'USD').
    :type moneda_origen: str
    :param moneda_destino: El código de la moneda de destino (ej. 'USD', 'PYG').
    :type moneda_destino: str
    :param user: El usuario que realiza la simulación, si está autenticado.
                 Se utiliza para aplicar bonificaciones.
    :type user: User, optional
    :returns: Un diccionario con el resultado de la simulación, incluyendo el monto recibido,
              la tasa aplicada, la bonificación aplicada y cualquier error.
    :rtype: dict
    """
    resultado = {
        'error': None,
        'monto_recibido': Decimal('0.0'),
        'tasa_aplicada': Decimal('0.0'),
        'bonificacion_aplicada': Decimal('0.0'),
        'comision_cotizacion': Decimal('0.0'), # Nuevo campo para la comisión de la cotización
        'monto_ajustado': False,
        'monto_maximo_posible': Decimal('0.0'),
    }

    moneda_origen_obj = None
    moneda_destino_obj = None
    cotizacion = None

    try:
        # --- Búsqueda de Monedas ---
        try:
            moneda_origen_obj = Moneda.objects.get(codigo=moneda_origen)
        except Moneda.DoesNotExist:
            raise Moneda.DoesNotExist(f"Moneda de origen '{moneda_origen}' no encontrada.")

        try:
            moneda_destino_obj = Moneda.objects.get(codigo=moneda_destino)
        except Moneda.DoesNotExist:
            raise Moneda.DoesNotExist(f"Moneda de destino '{moneda_destino}' no encontrada.")

        # --- Validación de Monto Mínimo ---
        if monto_origen < moneda_origen_obj.minima_denominacion:
            raise ValueError(
                f"El monto mínimo para cambiar {moneda_origen} es {moneda_origen_obj.minima_denominacion}."
            )

        # --- Bonificación del Cliente ---
        bonificacion_pct = Decimal('0')
        if user and user.is_authenticated:
            # Se asume que user.clientes.first() podría devolver None si no hay cliente asociado.
            cliente = user.clientes.first()
            if cliente: # Verificar si el cliente no es None
                bonificacion_pct = cliente.bonificacion
            # No es necesario un try-except ObjectDoesNotExist aquí, ya que .first() devuelve None, no lanza ObjectDoesNotExist.

        # --- Determinar Tipo de Transacción y Obtener Cotización ---
        if moneda_origen == 'PYG' and moneda_destino != 'PYG':
            # VENTA DE DIVISA (La casa de cambios VENDE USD, EUR, etc. al cliente)
            try:
                cotizacion = Cotizacion.objects.get(moneda_base__codigo='PYG', moneda_destino__codigo=moneda_destino)
            except Cotizacion.DoesNotExist:
                raise Cotizacion.DoesNotExist(f"No se encontró cotización para PYG -> {moneda_destino}.")

            comision_vta = cotizacion.comision_venta
            bonificacion_monto = comision_vta * (bonificacion_pct / Decimal('100'))
            tasa_final = (cotizacion.valor_venta + comision_vta) - bonificacion_monto
            
            if tasa_final <= 0:
                raise ValueError(f"Tasa de cambio de venta inválida para {moneda_destino}.")
            
            monto_recibido = monto_origen / tasa_final
            resultado['comision_cotizacion'] = comision_vta # Guardar la comisión de venta

            # Ajuste por denominaciones disponibles
            ajuste = ajustar_monto_a_denominaciones_disponibles(
                monto_recibido, moneda_destino_obj, 'venta'
            )
            monto_recibido_ajustado = ajuste['monto_ajustado']

            if ajuste['ajustado']:
                monto_recibido = monto_recibido_ajustado
                # Recalcular el monto_origen basado en el monto_recibido ajustado
                # Redondear hacia arriba para favorecer a la casa de cambios y asegurar enteros
                monto_origen = (monto_recibido * tasa_final).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                resultado['monto_ajustado'] = True
                resultado['monto_maximo_posible'] = ajuste['monto_maximo_posible']
                resultado['monto_origen_ajustado'] = monto_origen # Añadir el monto_origen ajustado

        elif moneda_origen != 'PYG' and moneda_destino == 'PYG':
            # COMPRA DE DIVISA (La casa de cambios COMPRA USD, EUR, etc. al cliente)
            try:
                cotizacion = Cotizacion.objects.get(moneda_base__codigo='PYG', moneda_destino__codigo=moneda_origen)
            except Cotizacion.DoesNotExist:
                raise Cotizacion.DoesNotExist(f"No se encontró cotización para {moneda_origen} -> PYG.")

            comision_com = cotizacion.comision_compra
            descuento_comision = comision_com * (bonificacion_pct / Decimal('100'))
            comision_final = comision_com - descuento_comision
            # CORRECCIÓN: La comisión de compra se resta del precio base para determinar el pago final al cliente.
            tasa_final = cotizacion.valor_compra - comision_final
            
            bonificacion_monto = descuento_comision
            
            if tasa_final <= 0:
                raise ValueError(f"Tasa de cambio de compra inválida para {moneda_origen}.")
                
            monto_recibido = monto_origen * tasa_final
            resultado['comision_cotizacion'] = comision_com # Guardar la comisión de compra

        else:
            raise ValueError("La simulación debe ser entre PYG y una moneda extranjera.")

        # --- Cuantificación Final y Validación ---
        monto_recibido = monto_recibido.quantize(
            Decimal('1') / (Decimal('10') ** moneda_destino_obj.decimales),
            rounding=ROUND_HALF_UP
        )

        if monto_recibido < moneda_destino_obj.minima_denominacion:
            raise ValueError(
                f"El monto a recibir ({monto_recibido} {moneda_destino_obj.codigo}) es menor a la denominación mínima de {moneda_destino_obj.minima_denominacion} {moneda_destino_obj.codigo}."
            )

        resultado.update({
            'tasa_aplicada': tasa_final,
            'bonificacion_aplicada': bonificacion_monto,
            'monto_recibido': monto_recibido,
            'monto_origen': monto_origen # Asegurarse de que el monto_origen final esté en el resultado
        })

    # Capturar errores específicos con mensajes más informativos
    except Moneda.DoesNotExist as e:
        resultado['error'] = f"Error en la simulación: {str(e)}" # str(e) ahora incluirá el código de la moneda
    except Cotizacion.DoesNotExist as e:
        resultado['error'] = f"Error en la simulación: {str(e)}" # str(e) ahora incluirá el par de monedas
    except ValueError as e:
        resultado['error'] = f"Error en la simulación: {str(e)}"
    except Exception as e:
        # Fallback para cualquier otro error inesperado
        resultado['error'] = f"Error inesperado en la simulación: {str(e)}"

    return resultado
