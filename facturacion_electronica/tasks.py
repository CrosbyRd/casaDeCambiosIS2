from celery import shared_task
from django.utils import timezone
from .services import FacturaSeguraAPIClient
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
    return (not cdc) or str(cdc).upper().startswith("SIMULATED")


import decimal

def _to_int(value):
    try:
        return int(value)
    except Exception:
        return 0

def _to_decimal(value, decimal_places=8):
    try:
        return decimal.Decimal(str(value)).quantize(decimal.Decimal(f"1e-{decimal_places}")).normalize()
    except Exception:
        return decimal.Decimal("0.00").normalize()

def _format_decimal_to_str(value, decimal_places=8):
    """
    Formatea un Decimal a string, eliminando ceros finales y el punto decimal
    si el valor es un entero.
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
    dTotOpeItem = _to_decimal(dTotOpeItem)
    dPropIVA = _to_decimal(dPropIVA)
    dTasaIVA = _to_decimal(dTasaIVA)

    if iAfecIVA in ["1", "4"]:
        if (decimal.Decimal("10000") + (dTasaIVA * dPropIVA)) == 0:
            return decimal.Decimal("0")
        return (decimal.Decimal("100") * dTotOpeItem * dPropIVA) / (decimal.Decimal("10000") + (dTasaIVA * dPropIVA))
    return decimal.Decimal("0")

def _calcular_liq_iva_item(dBasGravIVA, dTasaIVA):
    dBasGravIVA = _to_decimal(dBasGravIVA)
    dTasaIVA = _to_decimal(dTasaIVA)
    return dBasGravIVA * (dTasaIVA / decimal.Decimal("100"))

def _calcular_bas_exe(iAfecIVA, dTotOpeItem, dPropIVA, dTasaIVA):
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
    DE 'resumido' con nomenclatura alineada al XML del profe / SIFEN:
      - Bloque Emisor con sufijo Emi (dNomEmi, dDirEmi, dTelEmi, dEmailE, cDepEmi, dDesDepEmi, cCiuEmi, dDesCiuEmi)
      - Mínimos globales: iTipTra, iTImp, cMoneOpe, dCondTiCam, dTiCam, iCondOpe
      - Receptor básico y 1..N ítems exentos (ajusta si tu caso requiere IVA)
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

    comision = getattr(transaccion, "comision_aplicada", 0) or 0
    # La comisión siempre debe estar en PYG para la factura si la moneda de operación es PYG
    comision_pyg = _to_int(comision if codigo_origen == "PYG" or codigo_dest == "PYG" else comision * tasa) if comision > 0 else 0
    
    total_gs = monto_operacion_pyg + comision_pyg
    monto_operacion_gs = monto_operacion_pyg # Renombrado para claridad

    # === Cliente / receptor ===
    cliente = getattr(transaccion, "cliente", None)
    nombre_cliente = (
        getattr(cliente, "nombre", None)
        or (getattr(cliente, "get_full_name", lambda: None)() or None)
        or "CLIENTE TEST"
    )
    email_cliente = getattr(cliente, "email", None) or email_receptor or "receptor@test.com"
    ruc_rec = getattr(cliente, "ruc", None)
    dv_rec = getattr(cliente, "dv", None)
    dNumIDRec = getattr(cliente, "documento", None) or "0"

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
    if comision_pyg > 0: # Usar comision_pyg en lugar de comision_gs
        items.append({
            "dCodInt": "COMISION-FX",
            "dDesProSer": "Comisión por servicio de cambio",
            "cUniMed": "77",
            "dCantProSer": "1",
            "dPUniProSer": _format_decimal_to_str(comision_pyg),
            "dTiCamIt": "",
            "dTotBruOpeItem": _format_decimal_to_str(comision_pyg),
            "dDescItem": _format_decimal_to_str(0),
            "dPorcDesIt": _format_decimal_to_str(0),
            "dDescGloItem": _format_decimal_to_str(0),
            "dAntPreUniIt": _format_decimal_to_str(0),
            "dAntGloPreUniIt": _format_decimal_to_str(0),
            "dTotOpeItem": _format_decimal_to_str(comision_pyg),
            "dTotOpeGs": "",
            "iAfecIVA": "3", # Commission is exempt
            "dPropIVA": "0",
            "dTasaIVA": "0",
            "dBasGravIVA": _format_decimal_to_str(_calcular_bas_grav_iva("3", comision_pyg, "0", "0")),
            "dLiqIVAItem": _format_decimal_to_str(_calcular_liq_iva_item(_calcular_bas_grav_iva("3", comision_pyg, "0", "0"), "0")),
            "dBasExe": _format_decimal_to_str(_calcular_bas_exe("3", comision_pyg, "0", "0")),
        })

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
        "dDVEmi": str(getattr(emisor, "dv_ruc", "")),
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
        "cMoneOpe": "PYG" if codigo_dest == "PYG" else "USD",
        "dCondTiCam": "1",
        "dTiCam": "1" if codigo_dest == "PYG" else _format_decimal_to_str(tasa, decimal_places=0),
        "iCondOpe": "1",  # 1=Contado
        # Receptor
        "iNatRec": "1",
        "iTiOpe": "1",
        "cPaisRec": "PRY",
        "iTiContRec": "1", # Corregido a "1" (string) según XML de ejemplo
        "dRucRec": str(ruc_rec) if ruc_rec else "80000000",
        "dDVRec": str(dv_rec) if dv_rec is not None else "0",
        "iTipIDRec": "0",
        "dNumIDRec": str(dNumIDRec),
        "dNomRec": nombre_cliente,
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
    Flujo recomendado por la doc de ESI:
    1) construir DE 'resumido' (si no fue provisto)
    2) calcular_de (contrato estricto: params={"DE":...}) -> devuelve DE con campos calculados
    3) generar_de (solo DE) -> CDC y persistencia (vía services)
    4) (si no es simulación) agendar consulta de estado
    """
    try:
        client = FacturaSeguraAPIClient(emisor_id)
        tx = Transaccion.objects.get(pk=transaccion_id)

        # 1) DE resumido (o usar el completo provisto)
        emisor = client.emisor
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
    Consulta de estado SIFEN con reintentos solo en estados/errores recuperables.
    No consulta ni reintenta si:
      - el documento es simulado
      - el CDC es simulado
      - SIFEN responde que el RUC del CDC no coincide con dRucEm (error no recuperable)
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
    Solicita cancelación y reconsulta estado.
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
    Solicita inutilización y reconsulta estado.
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
    Reconsulta documentos en proceso.
    """
    for de in DocumentoElectronico.objects.filter(
        estado_sifen__in=["pendiente_aprobacion"]
    ):
        get_estado_sifen_task.delay(de.id)
