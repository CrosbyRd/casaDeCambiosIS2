# pagos/services.py

def ejecutar_acreditacion_a_cliente(transaccion):
    """
    Simula la transferencia de dinero (PYG) a la cuenta del cliente.
    
    Esta función actúa como un "contrato" para el resto del sistema.
    En el futuro, la lógica interna de esta función se reemplazará
    por la integración real con un proveedor de pagos (ej. SIPAP),
    sin necesidad de cambiar el código que la llama.

    Args:
        transaccion (Transaccion): La instancia de la transacción que debe ser pagada.

    Returns:
        bool: True si la acreditación simulada fue exitosa, False en caso contrario.
    """
    print("="*50)
    print(f"INFO: [SIMULACIÓN DE PAGO] Iniciando acreditación para la transacción {transaccion.id}.")
    print(f"INFO: -> Cliente: {transaccion.cliente.get_full_name()}")
    if transaccion.medio_acreditacion_cliente:
        print(f"INFO: -> Medio de Acreditación: {transaccion.medio_acreditacion_cliente.id}")
    else:
        print("WARN: -> No se especificó un medio de acreditación.")
    
    print(f"INFO: -> Monto a acreditar: {transaccion.monto_destino} {transaccion.moneda_destino.codigo}")
    print("="*50)
    
    # En una implementación real, aquí habría lógica para manejar posibles fallos.
    # Para la simulación, siempre asumimos que es exitosa.
    return True
