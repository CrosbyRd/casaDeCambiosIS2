from django.utils.timezone import now
from django.db.models import Sum
from configuracion.models import TransactionLimit
from transacciones.models import Transaccion
from monedas.models import Moneda
from decimal import Decimal
from core.logic import calcular_simulacion

def validar_limite_transaccion(cliente, monto, moneda_origen, moneda_destino):
    """
    Valida que el cliente no exceda su límite diario en moneda base (PYG).
    Convierte todas las transacciones previas y la actual a PYG.
    """

    # Obtener la moneda base (PYG)
    moneda_base = Moneda.objects.get(codigo='PYG')
    
    # Obtener el límite global para la moneda base
    limite_cfg = TransactionLimit.objects.filter(moneda=moneda_base).first()
    if not limite_cfg:
        return False, f"No está configurado un límite para la moneda base {moneda_base.codigo}."
    
    limite_diario = limite_cfg.monto_diario

    # Convertir el monto actual a moneda base (PYG)
    if moneda_origen != moneda_base.codigo:
        resultado = calcular_simulacion(monto, moneda_origen, moneda_base.codigo, user=None)
        if resultado['error']:
            return False, resultado['error']
        monto_en_base = Decimal(resultado['monto_recibido'])
    else:
        monto_en_base = Decimal(monto)

    hoy = now().date()

    # Obtener todas las transacciones del cliente realizadas hoy
    transacciones_hoy = Transaccion.objects.filter(
        cliente=cliente, # <--- Debe usar la variable cliente
        fecha_creacion__date=hoy
    )
    total_hoy = Decimal(0)
    
    # Sumar las transacciones previas del cliente para el día de hoy
    for t in transacciones_hoy:
        # Convertir cada transacción a moneda base (PYG)
        if t.moneda_origen.codigo != moneda_base.codigo:
            sim = calcular_simulacion(t.monto_origen, t.moneda_origen.codigo, moneda_base.codigo, user=None)
            if sim['error']:
                return False, sim['error']
            total_hoy += Decimal(sim['monto_recibido'])
        else:
            total_hoy += Decimal(t.monto_origen)

    # Sumar el monto actual al total de transacciones del día
    if total_hoy + monto_en_base > limite_diario:
        disponible = limite_diario - total_hoy
        return False, f"Límite diario excedido. Disponible: {disponible} {moneda_base.codigo}."

    return True, ""  # Si el límite no se excede, se permite la transacción.
