# core/simulacion_data.py
from decimal import Decimal

"""
Módulo de datos simulados para el desarrollo independiente del simulador.
Estos datos serán reemplazados por consultas a la base de datos una vez que
los modelos de Cotizacion, Moneda y Segmento estén estables.
"""

# Usamos Decimal para mantener la consistencia con el resto de la aplicación.
COTIZACIONES_SIMULADAS = {
    'USD': {
        'nombre': 'Dólar Americano',
        'precio_base_compra': Decimal('7300.00'),
        'precio_base_venta': Decimal('7450.00'),
        'comision_compra': Decimal('50.00'),
        'comision_venta': Decimal('100.00'),
    },
    'EUR': {
        'nombre': 'Euro',
        'precio_base_compra': Decimal('8100.00'),
        'precio_base_venta': Decimal('8300.00'),
        'comision_compra': Decimal('60.00'),
        'comision_venta': Decimal('120.00'),
    },
    'ARS': {
        'nombre': 'Peso Argentino',
        'precio_base_compra': Decimal('7.5'),
        'precio_base_venta': Decimal('9.5'),
        'comision_compra': Decimal('0.5'),
        'comision_venta': Decimal('1.0'),
    },
}

BONIFICACIONES_SIMULADAS = {
    # Porcentaje de descuento sobre la comisión
    'MINORISTA': Decimal('0'),
    'CORPORATIVO': Decimal('5'),
    'VIP': Decimal('10'),
}