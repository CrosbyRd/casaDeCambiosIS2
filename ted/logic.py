# ted/logic.py
from decimal import Decimal
from monedas.models import TedInventario

def ajustar_monto_a_denominaciones_disponibles(monto, moneda, tipo_operacion):
    """
    Ajusta un monto a las denominaciones disponibles en el inventario del Tauser (Terminal de Entrega de Divisas).

    Esta función tiene como propósito calcular el monto que puede ser efectivamente entregado o recibido
    en una transacción de compra o venta de divisas, considerando las denominaciones de billetes disponibles
    en el inventario físico del Tauser.

    El comportamiento varía según el tipo de operación:

    - **Compra**: cuando la casa de cambios **compra divisas** al cliente, no existen restricciones en las
      denominaciones recibidas (ya que el cliente puede entregar cualquier combinación de billetes).
      En este caso, el monto no se ajusta, pero se calcula el monto máximo posible en base al inventario.
    
    - **Venta**: cuando la casa de cambios **vende divisas** al cliente, el monto debe ajustarse a las
      denominaciones disponibles en el inventario. El sistema busca la mejor combinación de billetes
      disponibles (de mayor a menor valor) que no supere el monto solicitado y que respete las cantidades
      en stock.

    El ajuste no intenta hacer una combinación exacta tipo "cambio exacto", sino que aproxima el monto
    a la suma más cercana posible sin exceder el monto solicitado, de acuerdo con el inventario actual.

    :param monto: 
        Monto total solicitado para la operación.  
        Se interpreta como una cantidad monetaria a ajustar según disponibilidad.
        Debe ser una instancia de :class:`decimal.Decimal`.
    :type monto: Decimal

    :param moneda: 
        Instancia del modelo :class:`monedas.models.Moneda` que representa la moneda de la transacción
        (por ejemplo, USD, EUR, BRL, etc.).  
        Se utiliza para filtrar las denominaciones correspondientes en el inventario.
    :type moneda: Moneda

    :param tipo_operacion: 
        Tipo de operación que define la lógica del ajuste.  
        Acepta los valores:
        
        - ``'compra'`` → la casa de cambio compra divisas al cliente (no se ajusta el monto).
        - ``'venta'`` → la casa de cambio vende divisas al cliente (ajuste basado en inventario).
    :type tipo_operacion: str

    :returns: 
        Un diccionario con la información del resultado del ajuste, con las siguientes claves:

        - ``'monto_ajustado'`` (:class:`decimal.Decimal`): monto que efectivamente puede entregarse o recibirse según las denominaciones disponibles.
        - ``'monto_maximo_posible'`` (:class:`decimal.Decimal`): monto total que podría cubrirse utilizando todo el inventario disponible.
        - ``'ajustado'`` (bool): indica si el monto fue modificado respecto al monto original (`True` si se ajustó, `False` si no fue necesario).

    :rtype: dict

    :raises ValueError:
        Si el parámetro ``tipo_operacion`` no corresponde a un valor reconocido.

    **Lógica del ajuste para venta:**
    
    1. Se obtiene el inventario filtrado por moneda y con cantidad disponible mayor a cero.
    2. Se ordena el inventario de mayor a menor valor de denominación.
    3. Se recorre cada denominación calculando cuántos billetes se pueden utilizar sin exceder el monto restante.
    4. Se actualiza el monto ajustado y el monto restante en cada iteración.
    5. Se devuelve el resultado final con el monto efectivamente ajustado y el máximo posible.

    **Ejemplo de uso:**

    .. code-block:: python

        from decimal import Decimal
        from monedas.models import Moneda
        from ted.logic import ajustar_monto_a_denominaciones_disponibles

        usd = Moneda.objects.get(codigo="USD")

        resultado = ajustar_monto_a_denominaciones_disponibles(
            monto=Decimal('157'),
            moneda=usd,
            tipo_operacion='venta'
        )

        print(resultado)
        # {
        #   'monto_ajustado': Decimal('150'),
        #   'monto_maximo_posible': Decimal('2500'),
        #   'ajustado': True
        # }

    **Notas técnicas:**

    - La función utiliza `select_related('denominacion')` para optimizar las consultas y reducir el número
      de accesos a la base de datos al acceder al valor de cada denominación.
    - El ordenamiento descendente por `denominacion__valor` garantiza que se utilicen primero los billetes
      de mayor valor, reduciendo la cantidad total de billetes necesarios.
    - El cálculo del monto máximo posible (`monto_maximo_posible`) es útil para verificar si una operación
      solicitada puede cubrirse completamente con el stock disponible.

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
