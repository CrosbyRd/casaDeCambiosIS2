from celery import shared_task
from django.utils import timezone
from .services import FacturaSeguraAPIClient
from .models import DocumentoElectronico, EmisorFacturaElectronica
from transacciones.models import Transaccion


# ----------------------------
# Helpers
# ----------------------------

def _is_simulated_cdc(cdc):
    return (not cdc) or str(cdc).upper().startswith("SIMULATED")


def _to_int(value):
    try:
        return int(value)
    except Exception:
        return 0



def _build_de_resumido_desde_transaccion(transaccion, emisor, email_receptor="receptor@test.com"):
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

    if codigo_dest == "PYG":
        monto_operacion_gs = _to_int(getattr(transaccion, "monto_destino", 0) or 0)
    else:
        monto_operacion_gs = _to_int((getattr(transaccion, "monto_origen", 0) or 0) * tasa)

    comision = getattr(transaccion, "comision_aplicada", 0) or 0
    comision_gs = _to_int(comision if codigo_dest == "PYG" else comision * tasa) if comision > 0 else 0
    total_gs = monto_operacion_gs + comision_gs

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
            "dPUniProSer": str(monto_operacion_gs),
            "iAfecIVA": "3",  # 3=Exento (ajusta si tu régimen requiere IVA)
            "dPropIVA": "0",
            "dTasaIVA": "0",
        }
    ]
    if comision_gs > 0:
        items.append({
            "dCodInt": "COMISION-FX",
            "dDesProSer": "Comisión por servicio de cambio",
            "cUniMed": "77",
            "dCantProSer": "1",
            "dPUniProSer": str(comision_gs),
            "iAfecIVA": "3",
            "dPropIVA": "0",
            "dTasaIVA": "0",
        })

    # === Actividades económicas como lista de objetos (cActEco + descripción opcional) ===
    act_list = []
    if getattr(emisor, "actividad_economica_principal", None):
        act_list.append({"cActEco": str(emisor.actividad_economica_principal), "dDesActEco": ""})
    for code in (getattr(emisor, "actividades_economicas", []) or []):
        act_list.append({"cActEco": str(code), "dDesActEco": ""})

    # === Bloque Emisor (sufijo Emi) + mínimos globales ===
    de = {
        # Emisor
        "dRucEm": str(getattr(emisor, "ruc", "")),
        "dDVEmi": str(getattr(emisor, "dv_ruc", "")),
        "dNomEmi": getattr(emisor, "nombre", "") or "",
        "dDirEmi": getattr(emisor, "direccion", "") or "",
        "dNumCas": getattr(emisor, "numero_casa", "") or "",
        "cDepEmi": getattr(emisor, "codigo_departamento", "") or "",
        "dDesDepEmi": getattr(emisor, "descripcion_departamento", "") or "",
        "cCiuEmi": getattr(emisor, "codigo_ciudad", "") or "",
        "dDesCiuEmi": getattr(emisor, "descripcion_ciudad", "") or "",
        "dTelEmi": getattr(emisor, "telefono", "") or "",
        "dEmailE": getattr(emisor, "email_emisor", "") or "",
        "gActEco": act_list,
        "dEst": getattr(emisor, "establecimiento", "001") or "001",
        "dPunExp": getattr(emisor, "punto_expedicion", "003") or "003",
        "dNumTim": str(getattr(emisor, "numero_timbrado_actual", "") or ""),
        # Documento
        "iTiDE": "1",    # 1=Factura electrónica
        "iTipEmi": "1",  # 1=Normal
        "dFeEmiDE": timezone.now().strftime("%Y-%m-%dT%H:%M:%S"),
        # Mínimos globales (ajusta según tu régimen)
        "iTipTra": "1",  # 1=Venta de mercaderías/servicios (genérico)
        "iTImp": "1",    # 1=IVA (aunque los ítems estén exentos; la API lo admite)
        "cMoneOpe": "PYG" if codigo_dest == "PYG" else "USD",
        "dCondTiCam": "1",
        "dTiCam": "1" if codigo_dest == "PYG" else str(int(tasa)),
        "iCondOpe": "1",  # 1=Contado
        # Receptor
        "iNatRec": "1",
        "iTiOpe": "1",
        "cPaisRec": "PRY",
        "iTiContRec": "1",
        "dRucRec": str(ruc_rec) if ruc_rec else "80000000",
        "dDVRec": str(dv_rec) if dv_rec is not None else "0",
        "iTipIDRec": "0",
        "dNumIDRec": str(dNumIDRec),
        "dNomRec": nombre_cliente,
        "dEmailRec": email_cliente,
        # Pago contado simple
        "gPaConEIni": [
            {"iTiPago": "5", "dMonTiPag": str(total_gs), "cMoneTiPag": "PYG", "dTiCamTiPag": "1"}
        ],
        # Ítems
        "gCamItem": items,
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
    Flujo correcto ESI:
    1) construir DE 'resumido' (si no fue provisto)
    2) calcular_de -> devuelve DE con campos calculados
    3) generar_de -> asigna dNumDoc del rango / inyecta datos del emisor / CDC
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
            json_de_resumido = _build_de_resumido_desde_transaccion(
                tx, emisor=emisor, email_receptor=email_receptor
            )

        # 2) calcular_de
        calc_resp = client.calcular_de(json_de_resumido)
        if calc_resp.get("code", -1) != 0:
            raise Exception(f"Error calcular_de: {calc_resp}")

        # tomar DE enriquecido si vino, sino usamos el resumido
        de_completo = (calc_resp.get("results") or [{}])[0].get("DE") or json_de_resumido

        # 3) generar_de
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
        if "-80001" in msg or "no tiene permiso" in msg:
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
            # si tu modelo tiene este campo:
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
