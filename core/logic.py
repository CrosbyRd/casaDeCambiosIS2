# core/logic.py
from decimal import Decimal, ROUND_HALF_UP
from .simulacion_data import COTIZACIONES_SIMULADAS, BONIFICACIONES_SIMULADAS

def calcular_simulacion(monto_origen: Decimal, moneda_origen: str, moneda_destino: str, tipo_cliente: str = 'MINORISTA') -> dict:
    """Calcula el resultado de una simulación de cambio usando datos simulados.

    Esta función implementa la lógica de negocio para la compra y venta de divisas
    basándose en un diccionario de datos en lugar de la base de datos, permitiendo
    el desarrollo y pruebas de forma aislada.

    :param monto_origen: La cantidad de dinero a cambiar.
    :type monto_origen: Decimal
    :param moneda_origen: El código de la moneda de origen (ej. 'PYG').
    :type moneda_origen: str
    :param moneda_destino: El código de la moneda de destino (ej. 'USD').
    :type moneda_destino: str
    :param tipo_cliente: El segmento del cliente (ej. 'MINORISTA', 'VIP').
    :type tipo_cliente: str
    :raises ValueError: Si la combinación de monedas no es válida o la tasa resulta negativa.
    :return: Un diccionario con el resultado del cálculo.
    :rtype: dict
    """
    resultado = {
        'error': None,
        'monto_recibido': Decimal('0.0'),
        'tasa_aplicada': Decimal('0.0'),
        'bonificacion_aplicada': Decimal('0.0')
    }

    try:
        bonificacion_pct = BONIFICACIONES_SIMULADAS.get(tipo_cliente, Decimal('0'))

        if moneda_origen == 'PYG' and moneda_destino != 'PYG':
            # --- VENTA DE DIVISA (La casa de cambios VENDE USD, EUR, etc.) ---
            cotizacion = COTIZACIONES_SIMULADAS[moneda_destino]
            comision_vta = cotizacion['comision_venta']
            bonificacion_monto = comision_vta * (bonificacion_pct / Decimal('100'))
            tasa_final = (cotizacion['precio_base_venta'] + comision_vta) - bonificacion_monto
            
            if tasa_final <= 0: raise ValueError("Tasa de cambio de venta inválida.")
            monto_recibido = monto_origen / tasa_final

        elif moneda_origen != 'PYG' and moneda_destino == 'PYG':
            # --- COMPRA DE DIVISA (La casa de cambios COMPRA USD, EUR, etc.) ---
            cotizacion = COTIZACIONES_SIMULADAS[moneda_origen]
            comision_com = cotizacion['comision_compra']
            descuento_comision = comision_com * (bonificacion_pct / Decimal('100'))
            comision_final = comision_com - descuento_comision
            tasa_final = cotizacion['precio_base_compra'] - comision_final
            bonificacion_monto = descuento_comision
            
            if tasa_final <= 0: raise ValueError("Tasa de cambio de compra inválida.")
            monto_recibido = monto_origen * tasa_final

        else:
            raise ValueError("La simulación debe ser entre PYG y una moneda extranjera.")

        resultado.update({
            'tasa_aplicada': tasa_final,
            'bonificacion_aplicada': bonificacion_monto,
            'monto_recibido': monto_recibido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        })

    except (KeyError, ValueError) as e:
        resultado['error'] = f"Error en la simulación: {str(e)}"

    return resultado