# ted/logic.py
from decimal import Decimal
from monedas.models import TedInventario

def ajustar_monto_a_denominaciones_disponibles(monto, moneda, tipo_operacion):
    """
    Ajusta un monto a las denominaciones de billetes disponibles en el inventario del Tauser.
    """
    if tipo_operacion == 'compra':
        # Si la casa de cambios compra divisas, puede recibir cualquier denominación.
        # No se necesita ajuste.
        inventario = TedInventario.objects.filter(
            denominacion__moneda=moneda,
            cantidad__gt=0
        ).select_related('denominacion').order_by('-denominacion__valor')
        
        monto_maximo_posible = sum(
            item.denominacion.valor * item.cantidad for item in inventario
        )
        
        return {
            'monto_ajustado': monto,
            'monto_maximo_posible': monto_maximo_posible,
            'ajustado': False,
        }

    # Si la casa de cambios vende divisas, debe usar los billetes que tiene en stock.
    inventario = TedInventario.objects.filter(
        denominacion__moneda=moneda,
        cantidad__gt=0
    ).select_related('denominacion').order_by('-denominacion__valor')

    if not inventario.exists():
        return {
            'monto_ajustado': Decimal('0'),
            'monto_maximo_posible': Decimal('0'),
            'ajustado': True,
        }

    monto_maximo_posible = sum(
        item.denominacion.valor * item.cantidad for item in inventario
    )
    
    monto_a_entregar = min(monto, monto_maximo_posible)
    monto_ajustado = Decimal('0')
    monto_restante = monto_a_entregar

    for item in inventario:
        valor_denominacion = item.denominacion.valor
        cantidad_disponible = item.cantidad

        if monto_restante >= valor_denominacion:
            cantidad_a_usar = int(min(
                monto_restante // valor_denominacion,
                cantidad_disponible
            ))
            
            monto_ajustado += cantidad_a_usar * valor_denominacion
            monto_restante -= cantidad_a_usar * valor_denominacion

    return {
        'monto_ajustado': monto_ajustado,
        'monto_maximo_posible': monto_maximo_posible,
        'ajustado': monto_ajustado != monto,
    }
