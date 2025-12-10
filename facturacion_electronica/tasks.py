"""
Tareas asíncronas (Celery) de la app Facturación Electrónica.

.. module:: facturacion_electronica.tasks
   :synopsis: Tareas Celery para la gestión asíncrona de documentos electrónicos.

Este módulo define tareas Celery para la generación, consulta de estado,
cancelación e inutilización de documentos electrónicos, interactuando
con la API de Factura Segura y el sistema SIFEN.
"""
from celery import shared_task
from django.utils import timezone
from .services import FacturaSeguraAPIClient
from notificaciones.tasks import enviar_factura_por_email_task
from .models import DocumentoElectronico, EmisorFacturaElectronica
from transacciones.models import Transaccion


# Mapeo de códigos de actividad económica a descripciones
ACTIVIDADES_ECONOMICAS_MAP = {
    "62010": "Actividades de programación informática",
    "74909": "Otras actividades profesionales, científicas y técnicas n.c.p.",
    # Agrega más códigos y descripciones según sea necesario
}


# ----------------------------
# Helpers
# ----------------------------

def _is_simulated_cdc(cdc):
    """
    Verifica si un CDC (Código de Control) es un valor simulado.

    :param cdc: El CDC a verificar.
    :type cdc: str
    :return: True si el CDC es simulado, False en caso contrario.
    :rtype: bool
    """
    return (not cdc) or str(cdc).upper().startswith("SIMULATED")


import decimal

def _to_int(value):
    """
    Convierte un valor a entero, manejando posibles errores de conversión.

    :param value: El valor a convertir.
    :return: El valor convertido a entero o 0 si falla la conversión.
    :rtype: int
    """
    try:
        return int(value)
    except Exception:
        return 0

def _to_decimal(value, decimal_places=8):
    """
    Convierte un valor a un objeto Decimal, con una precisión específica.

    :param value: El valor a convertir.
    :type value: int, float, str
    :param decimal_places: Número de lugares decimales para la cuantificación.
    :type decimal_places: int
    :return: El valor convertido a Decimal o Decimal("0.00") si falla la conversión.
    :rtype: decimal.Decimal
    """
    try:
        return decimal.Decimal(str(value)).quantize(decimal.Decimal(f"1e-{decimal_places}")).normalize()
    except Exception:
        return decimal.Decimal("0.00").normalize()

def _format_decimal_to_str(value, decimal_places=8):
    """
    Formatea un valor (int, float, str o Decimal) a su representación en string,
    asegurando que sea un Decimal y eliminando ceros finales y el punto decimal
    si el valor resultante es un entero.

    :param value: El valor a formatear.
    :type value: int, float, str, decimal.Decimal
    :param decimal_places: Número de lugares decimales para la cuantificación inicial.
    :type decimal_places: int
    :return: La representación en string del valor formateado.
    :rtype: str
    """
    if isinstance(value, (int, float)):
        value = _to_decimal(value, decimal_places)
    elif not isinstance(value, decimal.Decimal):
        value = _to_decimal(value, decimal_places)

    # Normalizar para eliminar ceros finales innecesarios
    normalized_value = value.normalize()

    # Si es un entero después de normalizar, convertir a int y luego a str
    if normalized_value == normalized_value.to_integral_value():
        return str(int(normalized_value))
    # Si tiene decimales, convertir directamente a str
    return str(normalized_value)

def _calcular_bas_grav_iva(iAfecIVA, dTotOpeItem, dPropIVA, dTasaIVA):
    """
    Calcula la base gravada del IVA para un ítem.

    :param iAfecIVA: Código de afectación del IVA.
    :type iAfecIVA: str
    :param dTotOpeItem: Total de la operación del ítem.
    :type dTotOpeItem: decimal.Decimal o convertible
    :param dPropIVA: Proporción gravada del IVA.
    :type dPropIVA: decimal.Decimal o convertible
    :param dTasaIVA: Tasa de IVA.
    :type dTasaIVA: decimal.Decimal o convertible
    :return: La base gravada del IVA.
    :rtype: decimal.Decimal
    """
    dTotOpeItem = _to_decimal(dTotOpeItem)
    dPropIVA = _to_decimal(dPropIVA)
    dTasaIVA = _to_decimal(dTasaIVA)

    if iAfecIVA in ["1", "4"]:
        if (decimal.Decimal("10000") + (dTasaIVA * dPropIVA)) == 0:
            return decimal.Decimal("0")
        return (decimal.Decimal("100") * dTotOpeItem * dPropIVA) / (decimal.Decimal("10000") + (dTasaIVA * dPropIVA))
    return decimal.Decimal("0")

def _calcular_liq_iva_item(dBasGravIVA, dTasaIVA):
    """
    Calcula la liquidación del IVA para un ítem.

    :param dBasGravIVA: Base gravada del IVA.
    :type dBasGravIVA: decimal.Decimal o convertible
    :param dTasaIVA: Tasa de IVA.
    :type dTasaIVA: decimal.Decimal o convertible
    :return: La liquidación del IVA.
    :rtype: decimal.Decimal
    """
    dBasGravIVA = _to_decimal(dBasGravIVA)
    dTasaIVA = _to_decimal(dTasaIVA)
    return dBasGravIVA * (dTasaIVA / decimal.Decimal("100"))

def _calcular_bas_exe(iAfecIVA, dTotOpeItem, dPropIVA, dTasaIVA):
    """
    Calcula la base exenta para un ítem.

    :param iAfecIVA: Código de afectación del IVA.
    :type iAfecIVA: str
    :param dTotOpeItem: Total de la operación del ítem.
    :type dTotOpeItem: decimal.Decimal o convertible
    :param dPropIVA: Proporción gravada del IVA.
    :type dPropIVA: decimal.Decimal o convertible
    :param dTasaIVA: Tasa de IVA.
    :type dTasaIVA: decimal.Decimal o convertible
    :return: La base exenta.
    :rtype: decimal.Decimal
    """
    dTotOpeItem = _to_decimal(dTotOpeItem)
    dPropIVA = _to_decimal(dPropIVA)
    dTasaIVA = _to_decimal(dTasaIVA)

    if iAfecIVA == "4":
        if (decimal.Decimal("10000") + (dTasaIVA * dPropIVA)) == 0:
            return decimal.Decimal("0")
        return (decimal.Decimal("100") * dTotOpeItem * (decimal.Decimal("100") - dPropIVA)) / (decimal.Decimal("10000") + (dTasaIVA * dPropIVA))
    return decimal.Decimal("0")


def _build_de_resumido_desde_transaccion(transaccion, emisor, numero_documento_str, email_receptor="receptor@test.com"):
    """
    Construye un JSON de Documento Electrónico (DE) "resumido" a partir de una transacción.

    Este JSON sigue la nomenclatura alineada con el XML del profesor y el sistema SIFEN,
    incluyendo bloques para el emisor, mínimos globales, receptor e ítems.
    Se asume un "no contribuyente innominado" para el receptor en entornos de prueba.

    :param transaccion: La instancia de la transacción de la cual se extraen los datos.
    :type transaccion: :class:`transacciones.models.Transaccion`
    :param emisor: La instancia del emisor de factura electrónica.
    :type emisor: :class:`facturacion_electronica.models.EmisorFacturaElectronica`
    :param numero_documento_str: El número de documento formateado como string.
    :type numero_documento_str: str
    :param email_receptor: Email del receptor para el documento electrónico.
    :type email_receptor: str
    :return: Un diccionario que representa el JSON resumido del Documento Electrónico.
    :rtype: dict
    """
    # === Monedas / montos ===
    m_dest = getattr(transaccion, "moneda_destino", None)
    m_origen = getattr(transaccion, "moneda_origen", None)
    codigo_dest = getattr(m_dest, "codigo", "PYG") if m_dest else "PYG"
    codigo_origen = getattr(m_origen, "codigo", "PYG") if m_origen else "PYG"
    tasa = getattr(transaccion, "tasa_cambio_aplicada", 1) or 1

    # El monto en PYG de la operación es siempre el monto_origen si la moneda origen es PYG,
    # o el monto_destino si la moneda destino es PYG.
    # Si ninguna es PYG, entonces el monto_origen * tasa_cambio_aplicada.
    if codigo_origen == "PYG":
        monto_operacion_pyg = _to_int(getattr(transaccion, "monto_origen", 0) or 0)
    elif codigo_dest == "PYG":
        monto_operacion_pyg = _to_int(getattr(transaccion, "monto_destino", 0) or 0)
    else:
        # Si ninguna es PYG, asumimos que monto_origen es la base y se convierte a PYG
        monto_operacion_pyg = _to_int((getattr(transaccion, "monto_origen", 0) or 0) * tasa)

    total_gs = monto_operacion_pyg
    monto_operacion_gs = monto_operacion_pyg # Renombrado para claridad

    # === Cliente / receptor ===
    cliente = getattr(transaccion, "cliente", None)
    nombre_cliente = (
        getattr(cliente, "nombre", None)
        or (getattr(cliente, "get_full_name", lambda: None)() or None)
        or "CLIENTE TEST"
    )
    email_cliente = getattr(cliente, "email", None) or email_receptor or "receptor@test.com"
    # Hardcodeamos los datos del receptor para que siempre sea un "no contribuyente innominado"
    # para el entorno de pruebas, según lo solicitado.
    # Esto evita el error "1306 - TEST - RUC del receptor inexistente en la base de datos de Marangatu".
    
    # Valores fijos para "no contribuyente innominado"
    iNatRec_val = "2" # 2=no contribuyente
    iTiOpe_val = "2" # 2=B2C (Business to Consumer)
    cPaisRec_val = "PRY"
    iTiContRec_val = "" # No informar si D201 = 2
    dRucRec_val = "" # No informar si D201 = 2
    dDVRec_val = "" # No informar si D201 = 2

    # Usamos tipo de documento 5 ("otro"), válido para montos altos si hay un nombre real
    iTipIDRec_val = "5"     # 5=Innominado
    dNumIDRec_val = "1"     # numero permitido por SIFEN
    dNomRec_val =  nombre_cliente  # Si es Innominado, completar con "Sin Nombre"
    email_cliente = email_receptor or "receptor@test.com" # El email del receptor sigue siendo obligatorio para Factura Segura

    # === Ítems ===
    desc_fx = (
        f"Operación de cambio: {getattr(transaccion, 'monto_origen', 0)} {codigo_origen} "
        f"→ {getattr(transaccion, 'monto_destino', 0)} {codigo_dest} (TC {tasa})"
    )
    items = [
        {
            "dCodInt": f"FX-{codigo_origen}-{codigo_dest}",
            "dDesProSer": desc_fx,
            "cUniMed": "77",
            "dCantProSer": "1",
            "dPUniProSer": _format_decimal_to_str(monto_operacion_gs),
            "dTiCamIt": "", # hardcoded. Factura segura no soporta tipo de cambio por item.
            "dTotBruOpeItem": _format_decimal_to_str(monto_operacion_gs), # dPUniProSer * dCantProSer
            "dDescItem": _format_decimal_to_str(0), # Descuento unitario.
            "dPorcDesIt": _format_decimal_to_str(0), # dDescItem /dPUniProSer * 100
            "dDescGloItem": _format_decimal_to_str(0), # hardcoded. Factura Segura no soporta descuento global.
            "dAntPreUniIt": _format_decimal_to_str(0), # hardcoded. Factura Segura no soporta anticipo por item
            "dAntGloPreUniIt": _format_decimal_to_str(0), # hardcoded. Factura Segura no soporta anticipo global
            "dTotOpeItem": _format_decimal_to_str(monto_operacion_gs), # (dPUniProSer – dDescItem – dDescGloItem – dAntPreUniIt – dAntGloPreUniIt) * dCantProSer
            "dTotOpeGs": "", # hardcoded
            "iAfecIVA": "1",  # Default to 1=Gravado
            "dPropIVA": "100", # Default to 100%
            "dTasaIVA": "10", # Default to 10%
            "dBasGravIVA": _format_decimal_to_str(_calcular_bas_grav_iva("1", monto_operacion_gs, "100", "10")),
            "dLiqIVAItem": _format_decimal_to_str(_calcular_liq_iva_item(_calcular_bas_grav_iva("1", monto_operacion_gs, "100", "10"), "10")),
            "dBasExe": _format_decimal_to_str(_calcular_bas_exe("1", monto_operacion_gs, "100", "10")),
        }
    ]

    # Calculate summary fields
    dSubExe = _to_decimal("0")
    dSubExo = _to_decimal("0")
    dSub5 = _to_decimal("0")
    dSub10 = _to_decimal("0")
    dTotDesc = _to_decimal("0")
    dIVA5 = _to_decimal("0")
    dIVA10 = _to_decimal("0")
    dBaseGrav5 = _to_decimal("0")
    dBaseGrav10 = _to_decimal("0")

    for item in items:
        dTotOpeItem_dec = _to_decimal(item.get("dTotOpeItem", "0"))
        dBasGravIVA_dec = _to_decimal(item.get("dBasGravIVA", "0"))
        dLiqIVAItem_dec = _to_decimal(item.get("dLiqIVAItem", "0"))
        dBasExe_dec = _to_decimal(item.get("dBasExe", "0"))
        dTasaIVA_dec = _to_decimal(item.get("dTasaIVA", "0")) # This is where dTasaIVA_dec is defined
        iAfecIVA = item.get("iAfecIVA", "3")

        dTotDesc += _to_decimal(item.get("dDescItem", "0")) * _to_decimal(item.get("dCantProSer", "0"))

        if iAfecIVA == "3":
            dSubExe += dTotOpeItem_dec
        elif iAfecIVA == "4":
            dSubExe += dBasExe_dec

        if iAfecIVA == "2":
            dSubExo += dTotOpeItem_dec

        if dTasaIVA_dec == _to_decimal("5"):
            if iAfecIVA == "1":
                dSub5 += dTotOpeItem_dec
            elif iAfecIVA == "4":
                dSub5 += dBasGravIVA_dec + dLiqIVAItem_dec
            dIVA5 += dLiqIVAItem_dec
            dBaseGrav5 += dBasGravIVA_dec

        if dTasaIVA_dec == _to_decimal("10"):
            if iAfecIVA == "1":
                dSub10 += dTotOpeItem_dec
            elif iAfecIVA == "4":
                dSub10 += dBasGravIVA_dec + dLiqIVAItem_dec
            dIVA10 += dLiqIVAItem_dec
            dBaseGrav10 += dBasGravIVA_dec

    dTotOpe = dSubExe + dSubExo + dSub5 + dSub10
    dTotDescGlotem = _to_decimal("0") # hardcoded
    dTotAntItem = _to_decimal("0") # hardcoded
    dTotAnt = _to_decimal("0") # hardcoded
    dPorcDescTotal = _to_decimal("0") # hardcoded
    dDescTotal = dTotDesc + dTotDescGlotem
    dAnticipo = _to_decimal("0") # hardcoded
    dRedon = _to_decimal("0") # hardcoded
    dComi = _to_decimal("0") # hardcoded
    dTotGralOpe = dTotOpe - dRedon + dComi
    dLiqTotIVA5 = _to_decimal("0") # hardcoded
    dLiqTotIVA10 = _to_decimal("0") # hardcoded
    dIVAComi = _to_decimal("0") # hardcoded
    dTotIVA = dIVA10 + dIVA5 - dLiqTotIVA5 - dLiqTotIVA10 + dIVAComi
    dTBasGraIVA = dBaseGrav5 + dBaseGrav10
    dTotalGs = "" # Calculated if cMoneOpe != PYG

    # === Actividades económicas hardcodeadas según XML de ejemplo ===
    act_list = [
        {
            "cActEco": "62010",
            "dDesActEco": "Actividades de programación informática"
        },
        {
            "cActEco": "74909",
            "dDesActEco": "Otras actividades profesionales, científicas y técnicas n.c.p."
        }
    ]

    # === Contacto del emisor (robusto ante nombres de campo distintos) ===
    tel_emi = (
        getattr(emisor, "telefono", None)
        or getattr(emisor, "telefono_contacto", None)
        or ""
    )
    email_emi = (
        getattr(emisor, "email_emisor", None)
        or getattr(emisor, "email_contacto", None)
        or ""
    )

    # === Bloque Emisor (sufijo Emi) + mínimos globales ===
    de = {
        # Emisor
        "dRucEm": str(getattr(emisor, "ruc", "")),
        "dDVEmi": str(emisor.dv_ruc),
        "iTipCont": "2", # Tipo contribuyente del emisor
        "dNomEmi": getattr(emisor, "nombre", "") or "",
        "dDirEmi": getattr(emisor, "direccion", "") or "",
        "dNumCas": getattr(emisor, "numero_casa", "") or "",
        "cDepEmi": str(getattr(emisor, "codigo_departamento", "")) or "",
        "dDesDepEmi": getattr(emisor, "descripcion_departamento", "") or "",
        "cCiuEmi": str(getattr(emisor, "codigo_ciudad", "")) or "",
        "dDesCiuEmi": getattr(emisor, "descripcion_ciudad", "") or "",
        "dTelEmi": tel_emi,
        "dEmailE": email_emi,
        "gActEco": act_list,
        # Numeración fija (el profe exige 001-003)
        "dEst": getattr(emisor, "establecimiento", "001") or "001",
        "dPunExp": getattr(emisor, "punto_expedicion", "003") or "003",
        "dNumDoc": numero_documento_str, # Número de la Factura.
        "dFeIniT": emisor.fecha_inicio_timbrado.strftime("%Y-%m-%d"), # Fecha de inicio de timbrado
        "dNumTim": str(getattr(emisor, "numero_timbrado_actual", "") or ""),
        # Documento
        "iTiDE": "1",    # 1=Factura electrónica
        "iTipEmi": "1",  # 1=Normal
        "dFeEmiDE": timezone.now().strftime("%Y-%m-%dT%H:%M:%S"),
        # Mínimos globales (ajusta según tu régimen)
        "iTipTra": "1",  # 1=Venta de mercaderías/servicios (genérico)
        "iTImp": "5",    # Corregido a 5 según XML de ejemplo (IVA - Renta)
        "cMoneOpe": "PYG", # La moneda de la operación debe ser PYG si los ítems están en PYG
        "dCondTiCam": "1",
        "dTiCam": "", # No informar dTiCam si cMoneOpe es PYG
        "iCondOpe": "1",  # 1=Contado
        # Receptor
        "iNatRec": iNatRec_val,
        "iTiOpe": iTiOpe_val,
        "cPaisRec": cPaisRec_val,
        "iTiContRec": iTiContRec_val,
        "dRucRec": dRucRec_val,
        "dDVRec": dDVRec_val,
        "iTipIDRec": iTipIDRec_val,
        "dNumIDRec": dNumIDRec_val,
        "dNomRec": dNomRec_val,
        "dEmailRec": email_cliente,
        "iIndPres": "1", # Indicador de presencia.
        # Pago contado simple
        "gPaConEIni": [
            {"iTiPago": "5", "dMonTiPag": _format_decimal_to_str(total_gs), "cMoneTiPag": "PYG", "dTiCamTiPag": "1"}
        ],
        # Ítems
        "gCamItem": items,
        # Resumen de totales
        "dSubExe": _format_decimal_to_str(dSubExe),
        "dSubExo": _format_decimal_to_str(dSubExo),
        "dSub5": _format_decimal_to_str(dSub5),
        "dSub10": _format_decimal_to_str(dSub10),
        "dTotOpe": _format_decimal_to_str(dTotOpe),
        "dTotDesc": _format_decimal_to_str(dTotDesc),
        "dTotDescGlotem": _format_decimal_to_str(dTotDescGlotem),
        "dTotAntItem": _format_decimal_to_str(dTotAntItem),
        "dTotAnt": _format_decimal_to_str(dTotAnt),
        "dPorcDescTotal": _format_decimal_to_str(dPorcDescTotal),
        "dDescTotal": _format_decimal_to_str(dDescTotal),
        "dAnticipo": _format_decimal_to_str(dAnticipo),
        "dRedon": _format_decimal_to_str(dRedon),
        "dComi": _format_decimal_to_str(dComi),
        "dTotGralOpe": _format_decimal_to_str(dTotGralOpe),
        "dIVA5": _format_decimal_to_str(dIVA5),
        "dIVA10": _format_decimal_to_str(dIVA10),
        "dLiqTotIVA5": _format_decimal_to_str(dLiqTotIVA5),
        "dLiqTotIVA10": _format_decimal_to_str(dLiqTotIVA10),
        "dIVAComi": _format_decimal_to_str(dIVAComi),
        "dTotIVA": _format_decimal_to_str(dTotIVA),
        "dBaseGrav5": _format_decimal_to_str(dBaseGrav5),
        "dBaseGrav10": _format_decimal_to_str(dBaseGrav10),
        "dTBasGraIVA": _format_decimal_to_str(dTBasGraIVA),
        "dTotalGs": _format_decimal_to_str(dTotalGs) if codigo_dest != "PYG" and dTotalGs else "", # Calculated if cMoneOpe != PYG
        # Info adicional
        "dInfAdic": f"Tx {transaccion.id} • {getattr(transaccion, 'tipo_operacion', '')} • Estado {getattr(transaccion, 'estado', '')}",
        # Placeholders
        "CDC": "0", "dCodSeg": "0", "dDVId": "0", "dSisFact": "1",
    }
    return de


# ----------------------------
# Tareas
# ----------------------------

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def generar_factura_electronica_task(self, emisor_id, transaccion_id, json_de_completo=None, email_receptor="globalexchangea2@gmail.com"):
    """
    Tarea Celery para generar una factura electrónica.

    Implementa el flujo recomendado por la documentación de ESI:
    1. Construye un JSON de DE "resumido" si no se proporciona uno completo.
    2. Llama a la operación `calcular_de` de la API para obtener el DE con campos calculados.
    3. Llama a la operación `generar_de` de la API para crear el DE y persistir el :class:`DocumentoElectronico` localmente.
    4. Si no es una simulación, agenda una tarea para consultar el estado SIFEN del documento.

    Gestiona reintentos en caso de fallos recuperables y registra errores persistentes.

    :param self: Instancia de la tarea Celery (para `retry`).
    :param emisor_id: ID del emisor de factura electrónica.
    :type emisor_id: int or None
    :param transaccion_id: ID de la transacción asociada.
    :type transaccion_id: uuid.UUID
    :param json_de_completo: JSON completo del DE si ya está pre-construido.
    :type json_de_completo: dict or None
    :param email_receptor: Email del receptor para el documento electrónico.
    :type email_receptor: str
    :raises Exception: Si ocurre un error no recuperable o se exceden los reintentos.
    :return: Un diccionario con el estado de la tarea y el CDC si fue exitosa.
    :rtype: dict
    """
    try:
        # Si emisor_id es None, buscar un emisor por defecto
        if emisor_id is None:
            emisor = EmisorFacturaElectronica.objects.filter(activo=True).first()
            if not emisor:
                raise Exception("No se encontró ningún EmisorFacturaElectronica activo configurado.")
            emisor_id = emisor.id
        else:
            emisor = EmisorFacturaElectronica.objects.get(id=emisor_id)

        client = FacturaSeguraAPIClient(emisor_id)
        tx = Transaccion.objects.get(pk=transaccion_id)

        # 1) DE resumido (o usar el completo provisto)
        # El emisor ya se obtuvo arriba, no es necesario client.emisor
        if json_de_completo:
            json_de_resumido = json_de_completo
        else:
            # Reservar número de factura y avanzar el contador
            numero_factura_int, numero_factura_str = emisor.reservar_numero_y_avanzar()
            json_de_resumido = _build_de_resumido_desde_transaccion(
                tx, emisor=emisor, numero_documento_str=numero_factura_str, email_receptor=email_receptor
            )

        # 2) calcular_de – prioriza contrato estricto si existe
        if hasattr(client, "calcular_de_contrato_estricto"):
            de_completo = client.calcular_de_contrato_estricto(json_de_resumido)
        else:
            calc_resp = client.calcular_de(json_de_resumido)
            if calc_resp.get("code", -1) != 0:
                raise Exception(f"Error calcular_de: {calc_resp}")
            de_completo = (calc_resp.get("results") or [{}])[0].get("DE") or json_de_resumido

        # 3) generar_de – usamos el services para persistir el DocumentoElectronico
        #    (si actualizaste services con contrato estricto, ahí adentro ya se envía solo DE)
        doc_electronico = client.generar_de(de_completo, transaccion_id)

        # Actualizar estado de la transacción a 'completada' si es una operación de 'compra'
        if tx.tipo_operacion == 'compra':
            tx.estado = 'completada'
            tx.save(update_fields=['estado'])

        # 4) agendar consulta si corresponde
        if (
            doc_electronico
            and doc_electronico.estado_sifen != 'simulado'
            and doc_electronico.cdc
            and not _is_simulated_cdc(doc_electronico.cdc)
        ):
            get_estado_sifen_task.apply_async((doc_electronico.id,), countdown=60)

        return {"status": "success", "cdc": getattr(doc_electronico, "cdc", None)}

    except Exception as e:
        # No reintentar si es falta de permisos específicos
        msg = str(e).lower()
        if "-80001" in msg or "no tiene permiso" in msg or "sin permiso" in msg:
            doc = DocumentoElectronico.objects.filter(transaccion_asociada_id=transaccion_id).first()
            if doc:
                doc.estado_sifen = "error_api"
                doc.descripcion_estado = "ESI sin permiso para emitir para este RUC (code -80001)."
                doc.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "failed", "error": "ESI sin permiso (-80001)"}
        # Reintentos
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            doc = DocumentoElectronico.objects.filter(transaccion_asociada_id=transaccion_id).first()
            if doc:
                doc.estado_sifen = 'error_api'
                doc.descripcion_estado = f"Fallo persistente al generar DE: {e}"
                doc.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=10, default_retry_delay=300)
def get_estado_sifen_task(self, documento_electronico_id):
    """
    Tarea Celery para consultar el estado de un Documento Electrónico en SIFEN.

    Esta tarea consulta el estado de un documento electrónico y actualiza su estado
    localmente. Implementa una lógica de reintentos para errores recuperables
    y maneja casos específicos como documentos simulados o errores no recuperables
    (ej. RUC del CDC no coincide).

    También actualiza el estado de la transacción asociada a 'completada' si el
    documento es aprobado y envía la factura por email.

    :param self: Instancia de la tarea Celery (para `retry`).
    :param documento_electronico_id: ID del documento electrónico a consultar.
    :type documento_electronico_id: uuid.UUID
    :raises DocumentoElectronico.DoesNotExist: Si el documento no se encuentra.
    :raises Exception: Si ocurre un error no recuperable o se exceden los reintentos.
    :return: Un diccionario con el estado de la tarea y el estado SIFEN.
    :rtype: dict
    """
    try:
        doc_electronico = DocumentoElectronico.objects.get(id=documento_electronico_id)
        emisor = doc_electronico.emisor
        client = FacturaSeguraAPIClient(emisor.id)

        # Evitar consultas para documentos simulados o CDC simulado
        if doc_electronico.estado_sifen == 'simulado' or _is_simulated_cdc(doc_electronico.cdc):
            if not doc_electronico.descripcion_estado:
                doc_electronico.descripcion_estado = 'Estado simulado'
                doc_electronico.save(update_fields=["descripcion_estado"])
            return {"status": "success", "estado": doc_electronico.estado_sifen}

        if client.simulation_mode:
            # Modo sim: resolvemos localmente
            if doc_electronico.estado_sifen == 'pendiente_aprobacion':
                doc_electronico.estado_sifen = 'simulado'
                doc_electronico.descripcion_estado = 'Estado simulado: Aprobado'
                doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "success", "estado": doc_electronico.estado_sifen}

        # Llamada real a la API
        resp = client.get_estado_sifen(doc_electronico.cdc, emisor.ruc)

        # Manejo de errores no recuperables por mensaje
        msg = (resp.get("description") or "").strip()
        if "RUC del CDC no coincide" in msg:
            doc_electronico.estado_sifen = "error_api"
            doc_electronico.descripcion_estado = msg or "RUC del CDC no coincide con dRucEm"
            doc_electronico.json_respuesta_api = resp
            if hasattr(doc_electronico, "fecha_ultimo_cambio_estado"):
                doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
                doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
            else:
                doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api"])
            return {"status": "error", "detail": "RUC CDC != dRucEm"}

        # Respuesta exitosa
        if resp.get("code", -1) == 0 and resp.get("results"):
            info = resp["results"][0]
            est = (info.get("estado_sifen") or "").upper()

            if info.get("estado_inu") == "Aprobado":
                new_estado, new_desc = "inutilizado", "Documento inutilizado en SIFEN."
            elif info.get("estado_can") == "Aprobado":
                new_estado, new_desc = "cancelado", "Documento cancelado en SIFEN."
            elif est == "APROBADO":
                new_estado, new_desc = "aprobado", info.get("desc_sifen", "Aprobado en SIFEN.")
                # --- INICIO: Enviar factura por email (para pruebas) ---
                # Se envía cada vez que se consulta y el estado es 'aprobado'.
                enviar_factura_por_email_task.delay(doc_electronico.id)
                # --- FIN: Enviar factura por email (para pruebas) ---
            elif est == "APROBADO CON OBSERVACIÓN":
                new_estado, new_desc = "aprobado_obs", info.get("desc_sifen", "Aprobado con observación.")
            elif est == "RECHAZADO":
                new_estado, new_desc = "rechazado", info.get("desc_sifen", "Rechazado por SIFEN.")
            elif est in {"ERROR_SIFEN", "ERROR_ENVIO_LOTE", "REINTENTAR_LOTE", "ERROR_CONSULTA_LOTE"}:
                new_estado, new_desc = "error_sifen", (info.get("desc_sifen", "Error SIFEN.") + " " + info.get("error_sifen", "")).strip()
            elif est in {"SOL.APROBACION", "ENVIADO_A_SIFEN"}:
                new_estado, new_desc = "pendiente_aprobacion", "En proceso de aprobación en SIFEN."
            else:
                new_estado, new_desc = doc_electronico.estado_sifen, doc_electronico.descripcion_estado

            if new_estado != doc_electronico.estado_sifen or (new_desc or "") != (doc_electronico.descripcion_estado or ""):
                doc_electronico.estado_sifen = new_estado
                doc_electronico.descripcion_estado = new_desc
                doc_electronico.json_respuesta_api = resp
                if hasattr(doc_electronico, "fecha_ultimo_cambio_estado"):
                    doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
                    doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
                else:
                    doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api"])

            # Reintentar solo si no es estado final
            if new_estado not in {"aprobado", "aprobado_obs", "rechazado", "cancelado", "inutilizado", "error_sifen", "error_api"}:
                self.retry(countdown=300)

            return {"status": "success", "estado": new_estado}

        # Error de API recuperable/no determinístico → decidir si reintentar
        error_desc = resp.get("description", "Error desconocido al consultar estado")

        # Si es mismatch de RUC (por si vino en otro campo), no reintentar
        if "RUC del CDC no coincide" in error_desc:
            doc_electronico.estado_sifen = "error_api"
            doc_electronico.descripcion_estado = error_desc
            doc_electronico.json_respuesta_api = resp
            if hasattr(doc_electronico, "fecha_ultimo_cambio_estado"):
                doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
                doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
            else:
                doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api"])
            return {"status": "error", "detail": "RUC CDC != dRucEm"}

        # Otros errores: marcamos y reintentamos
        doc_electronico.estado_sifen = "error_api"
        doc_electronico.descripcion_estado = f"Error al consultar estado: {error_desc}"
        doc_electronico.json_respuesta_api = resp
        if hasattr(doc_electronico, "fecha_ultimo_cambio_estado"):
            doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
            doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
        else:
            doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api"])
        self.retry(exc=Exception(error_desc))

    except DocumentoElectronico.DoesNotExist:
        return {"status": "failed", "error": "Documento no encontrado"}
    except Exception as e:
        # Reintento general; pero si el mensaje es no recuperable, no reintentar
        msg = str(e)
        if "RUC del CDC no coincide" in msg:
            d = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if d:
                d.estado_sifen = "error_api"
                d.descripcion_estado = msg
                if hasattr(d, "fecha_ultimo_cambio_estado"):
                    d.fecha_ultimo_cambio_estado = timezone.now()
                    d.save(update_fields=["estado_sifen", "descripcion_estado", "fecha_ultimo_cambio_estado"])
                else:
                    d.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "error", "detail": "RUC CDC != dRucEm"}
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            d = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if d:
                d.estado_sifen = "error_api"
                d.descripcion_estado = f"Fallo persistente al consultar estado SIFEN: {e}"
                if hasattr(d, "fecha_ultimo_cambio_estado"):
                    d.fecha_ultimo_cambio_estado = timezone.now()
                    d.save(update_fields=["estado_sifen", "descripcion_estado", "fecha_ultimo_cambio_estado"])
                else:
                    d.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def solicitar_cancelacion_task(self, documento_electronico_id):
    """
    Tarea Celery para solicitar la cancelación de un Documento Electrónico.

    Envía una solicitud de cancelación a la API de Factura Segura y, si es exitosa,
    actualiza el estado local del documento a 'pendiente_cancelacion' y agenda
    una tarea para reconsultar su estado en SIFEN.

    Gestiona reintentos en caso de fallos recuperables.

    :param self: Instancia de la tarea Celery (para `retry`).
    :param documento_electronico_id: ID del documento electrónico a cancelar.
    :type documento_electronico_id: uuid.UUID
    :raises DocumentoElectronico.DoesNotExist: Si el documento no se encuentra.
    :raises Exception: Si ocurre un error no recuperable o se exceden los reintentos.
    :return: Un diccionario con el estado de la tarea y el estado de la solicitud.
    :rtype: dict
    """
    try:
        doc = DocumentoElectronico.objects.get(id=documento_electronico_id)
        emisor = doc.emisor
        client = FacturaSeguraAPIClient(emisor.id)

        if client.simulation_mode:
            doc.estado_sifen = "cancelado"
            doc.descripcion_estado = "Cancelación simulada"
            doc.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "success", "estado": "cancelado"}

        resp = client.solicitar_cancelacion(doc.cdc, emisor.ruc)
        if resp.get("code", -1) == 0:
            doc.estado_sifen = "pendiente_cancelacion"
            doc.descripcion_estado = "Solicitud de cancelación enviada."
            doc.json_respuesta_api = resp
            doc.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api"])
            get_estado_sifen_task.apply_async((doc.id,), countdown=60)
            return {"status": "success", "estado": "solicitud_enviada"}

        err = resp.get("description", "Error desconocido al solicitar cancelación")
        doc.descripcion_estado = f"Error al solicitar cancelación: {err}"
        doc.json_respuesta_api = resp
        doc.save(update_fields=["descripcion_estado", "json_respuesta_api"])
        raise Exception(f"Error de API al solicitar cancelación: {err}")

    except DocumentoElectronico.DoesNotExist:
        return {"status": "failed", "error": "Documento no encontrado"}
    except Exception as e:
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            d = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if d:
                d.estado_sifen = "error_api"
                d.descripcion_estado = f"Fallo persistente al solicitar cancelación: {e}"
                d.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def solicitar_inutilizacion_task(self, documento_electronico_id):
    """
    Tarea Celery para solicitar la inutilización de un Documento Electrónico.

    Envía una solicitud de inutilización a la API de Factura Segura y, si es exitosa,
    actualiza el estado local del documento a 'pendiente_inutilizacion' y agenda
    una tarea para reconsultar su estado en SIFEN.

    Gestiona reintentos en caso de fallos recuperables.

    :param self: Instancia de la tarea Celery (para `retry`).
    :param documento_electronico_id: ID del documento electrónico a inutilizar.
    :type documento_electronico_id: uuid.UUID
    :raises DocumentoElectronico.DoesNotExist: Si el documento no se encuentra.
    :raises Exception: Si ocurre un error no recuperable o se exceden los reintentos.
    :return: Un diccionario con el estado de la tarea y el estado de la solicitud.
    :rtype: dict
    """
    try:
        doc = DocumentoElectronico.objects.get(id=documento_electronico_id)
        emisor = doc.emisor
        client = FacturaSeguraAPIClient(emisor.id)

        if client.simulation_mode:
            doc.estado_sifen = "inutilizado"
            doc.descripcion_estado = "Inutilización simulada"
            doc.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "success", "estado": "inutilizado"}

        resp = client.solicitar_inutilizacion(
            ruc_emisor=emisor.ruc,
            tipo_de="1",  # 1 = Factura
            num_timbrado=doc.numero_timbrado,
            establecimiento=emisor.establecimiento,
            punto_exp=emisor.punto_expedicion,
            num_doc=doc.numero_documento,
        )
        if resp.get("code", -1) == 0:
            doc.estado_sifen = "pendiente_inutilizacion"
            doc.descripcion_estado = "Solicitud de inutilización enviada."
            doc.json_respuesta_api = resp
            doc.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api"])
            get_estado_sifen_task.apply_async((doc.id,), countdown=60)
            return {"status": "success", "estado": "solicitud_enviada"}

        err = resp.get("description", "Error desconocido al solicitar inutilización")
        doc.descripcion_estado = f"Error al solicitar inutilización: {err}"
        doc.json_respuesta_api = resp
        doc.save(update_fields=["descripcion_estado", "json_respuesta_api"])
        raise Exception(f"Error de API al solicitar inutilización: {err}")

    except DocumentoElectronico.DoesNotExist:
        return {"status": "failed", "error": "Documento no encontrado"}
    except Exception as e:
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            d = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if d:
                d.estado_sifen = "error_api"
                d.descripcion_estado = f"Fallo persistente al solicitar inutilización: {e}"
                d.save(update_fields=["estado_sifen", "descripcion_estado"])
            return {"status": "failed", "error": str(e)}


# (Opcional) para usar con Celery Beat si lo definiste en settings:
@shared_task
def consultar_estado_pendientes():
    """
    Tarea Celery para reconsultar periódicamente el estado de documentos electrónicos
    que se encuentran en estado 'pendiente_aprobacion'.

    Itera sobre los documentos pendientes y agenda una tarea `get_estado_sifen_task`
    para cada uno.
    """
    for de in DocumentoElectronico.objects.filter(
        estado_sifen__in=["pendiente_aprobacion"]
    ):
        get_estado_sifen_task.delay(de.id)
