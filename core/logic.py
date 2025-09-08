# core/logic.py
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth import get_user_model
from cotizaciones.models import Cotizacion
from monedas.models import Moneda
from clientes.models import Cliente

User = get_user_model()

def calcular_simulacion(monto_origen: Decimal, moneda_origen: str, moneda_destino: str, user: User = None) -> dict:
    """
    Calcula el resultado de una simulación de cambio utilizando datos reales de la base de datos,
    replicando la lógica de negocio original de comisiones y bonificaciones.

    :param monto_origen: La cantidad de dinero a cambiar.
    :param moneda_origen: El código de la moneda de origen (ej. 'PYG').
    :param moneda_destino: El código de la moneda de destino (ej. 'USD').
    :param user: El usuario que realiza la simulación (opcional).
    :return: Un diccionario con el resultado del cálculo.
    """
    resultado = {
        'error': None,
        'monto_recibido': Decimal('0.0'),
        'tasa_aplicada': Decimal('0.0'),
        'bonificacion_aplicada': Decimal('0.0')
    }

    try:
        # 1. Determinar la bonificación del cliente
        bonificacion_pct = Decimal('0')
        if user and user.is_authenticated:
            cliente = user.clientes.first()
            if cliente:
                bonificacion_pct = cliente.bonificacion

        # 2. Lógica de cálculo
        if moneda_origen == 'PYG' and moneda_destino != 'PYG':
            # --- VENTA DE DIVISA (La casa de cambios VENDE USD, EUR, etc.) ---
            cotizacion = Cotizacion.objects.get(moneda_base__codigo='PYG', moneda_destino__codigo=moneda_destino)
            
            comision_vta = cotizacion.comision_venta
            bonificacion_monto = comision_vta * (bonificacion_pct / Decimal('100'))
            tasa_final = (cotizacion.valor_venta + comision_vta) - bonificacion_monto
            
            if tasa_final <= 0:
                raise ValueError(f"Tasa de cambio de venta inválida para {moneda_destino}.")
            
            monto_recibido = monto_origen / tasa_final

        elif moneda_origen != 'PYG' and moneda_destino == 'PYG':
            # --- COMPRA DE DIVISA (La casa de cambios COMPRA USD, EUR, etc.) ---
            cotizacion = Cotizacion.objects.get(moneda_base__codigo='PYG', moneda_destino__codigo=moneda_origen)
            
            comision_com = cotizacion.comision_compra
            descuento_comision = comision_com * (bonificacion_pct / Decimal('100'))
            comision_final = comision_com - descuento_comision
            tasa_final = cotizacion.valor_compra - comision_final
            
            # La bonificación aplicada es el monto que se descontó de la comisión
            bonificacion_monto = descuento_comision
            
            if tasa_final <= 0:
                raise ValueError(f"Tasa de cambio de compra inválida para {moneda_origen}.")
                
            monto_recibido = monto_origen * tasa_final

        else:
            raise ValueError("La simulación debe ser entre PYG y una moneda extranjera.")

        resultado.update({
            'tasa_aplicada': tasa_final,
            'bonificacion_aplicada': bonificacion_monto,
            'monto_recibido': monto_recibido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        })

    except Cotizacion.DoesNotExist:
        resultado['error'] = f"No se encontró una cotización para el par de monedas solicitado."
    except Exception as e:
        resultado['error'] = f"Error en la simulación: {str(e)}"

    return resultado
