from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .services import FacturaSeguraAPIClient
from .models import DocumentoElectronico, EmisorFacturaElectronica
from transacciones.models import Transaccion


def _is_simulated_cdc(cdc):
    return (not cdc) or str(cdc).upper().startswith("SIMULATED")


def _to_int(value):
    try:
        return int(value)
    except Exception:
        return 0

def _build_de_resumido_desde_transaccion(transaccion, emisor, email_receptor="receptor@test.com"):
    """
    Builder de DE 'resumido' (mínimo pero con bloque de EMISOR) a partir de una Transaccion.
    Incluye:
      - Bloque del EMISOR: dRucEm, dDV, dEst, dPunExp, dNumTim, datos de contacto/dirección.
      - Receptor/cliente, ítems y montos en PYG.
    """
    # === Monedas / montos ===
    m_dest = getattr(transaccion, "moneda_destino", None)
    m_origen = getattr(transaccion, "moneda_origen", None)
    codigo_dest = getattr(m_dest, "codigo", "PYG") if m_dest else "PYG"
    codigo_origen = getattr(m_origen, "codigo", "PYG") if m_origen else "PYG"
    tasa = getattr(transaccion, "tasa_cambio_aplicada", 1) or 1

    def _to_int(value):
        try:
            return int(value)
        except Exception:
            return 0

    if codigo_dest == "PYG":
        monto_operacion_gs = _to_int(getattr(transaccion, "monto_destino", 0) or 0)
    else:
        monto_operacion_gs = _to_int((getattr(transaccion, "monto_origen", 0) or 0) * tasa)

    comision = getattr(transaccion, "comision_aplicada", 0) or 0
    if comision and comision > 0:
        comision_gs = _to_int(comision if codigo_dest == "PYG" else comision * tasa)
    else:
        comision_gs = 0

    total_gs = monto_operacion_gs + comision_gs

    # === Cliente / receptor ===
    cliente = getattr(transaccion, "cliente", None)
    nombre_cliente = getattr(cliente, "nombre", None) or getattr(cliente, "get_full_name", lambda: None)() or "CLIENTE TEST"
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
            "iAfecIVA": "3",  # Exento (ajusta si tu régimen requiere IVA)
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

    # === Bloque EMISOR (lo que pide la API para calcular_de) ===
    de = {
        # Emisor — claves más usadas por el ESI
        "dRucEm": str(getattr(emisor, "ruc", "")),                                # <- requerido
        "dDV": str(getattr(emisor, "dv_ruc", "")),                                 # DV del emisor (campo suele llamarse dDV)
        "dNomEm": getattr(emisor, "nombre", "") or "",
        "dDirEm": getattr(emisor, "direccion", "") or "",
        "dNumCas": getattr(emisor, "numero_casa", "") or "",
        "dDesCiu": getattr(emisor, "descripcion_ciudad", "") or "",
        "dDesDep": getattr(emisor, "descripcion_departamento", "") or "",
        "cDep": getattr(emisor, "codigo_departamento", "") or "",
        "dTelEm": getattr(emisor, "telefono", "") or "",
        "dEmailEm": getattr(emisor, "email_emisor", "") or "",
        "dActEco": getattr(emisor, "actividades_economicas", "") or "",
        "dEst": getattr(emisor, "establecimiento", "001") or "001",
        "dPunExp": getattr(emisor, "punto_expedicion", "003") or "003",
        "dNumTim": str(getattr(emisor, "numero_timbrado_actual", "") or ""),
        # Documento
        "iTipEmi": "1",  # Normal
        "iTiDE": "1",    # Factura electrónica
        "dFeEmiDE": timezone.now().strftime("%Y-%m-%dT%H:%M:%S"),
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
        # Condición / Moneda
        "iCondOpe": "1",                               # Contado
        "cMoneOpe": "PYG" if codigo_dest == "PYG" else "USD",
        "dCondTiCam": "1",
        "dTiCam": "1" if codigo_dest == "PYG" else str(int(tasa)),
        # Pago contado simple
        "gPaConEIni": [
            {"iTiPago": "5", "dMonTiPag": str(total_gs), "cMoneTiPag": "PYG", "dTiCamTiPag": "1"}
        ],
        # Ítems
        "gCamItem": items,
        # Info adicional
        "dInfAdic": f"Tx {transaccion.id} • {getattr(transaccion, 'tipo_operacion', '')} • Estado {getattr(transaccion, 'estado', '')}",
        # Placeholders
        "CDC": "0",
        "dCodSeg": "0",
        "dDVId": "0",
        "dSisFact": "1",
    }
    return de



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

        # 1) DE resumido
        emisor = client.emisor
        if not json_de_completo:
            json_de_resumido = _build_de_resumido_desde_transaccion(
                tx,
                emisor=emisor,
                email_receptor=email_receptor
            )
        else:
            json_de_resumido = json_de_completo


        # 2) calcular_de
        calc = client.calcular_de(json_de_resumido)
        if calc.get("code", -1) != 0 or not calc.get("results"):
            raise RuntimeError(f"Error calcular_de: {calc}")
        de_completo = calc["results"][0]["DE"]

        # 3) generar_de
        doc_electronico = client.generar_de(de_completo, transaccion_id)

        if (
            doc_electronico
            and doc_electronico.estado_sifen != 'simulado'
            and doc_electronico.cdc
            and not _is_simulated_cdc(doc_electronico.cdc)
        ):
            get_estado_sifen_task.apply_async((doc_electronico.id,), countdown=60)

        return {"status": "success", "cdc": getattr(doc_electronico, "cdc", None)}
    except Exception as e:
        # Reintentos
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            doc = DocumentoElectronico.objects.filter(transaccion_asociada_id=transaccion_id).first()
            if doc:
                doc.estado_sifen = 'error_api'
                doc.descripcion_estado = f"Fallo persistente al generar DE: {e}"
                doc.save()
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
            # Normalizamos la descripción si está vacía
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
            # No reintentar: guardamos como error_api y salimos
            doc_electronico.estado_sifen = "error_api"
            doc_electronico.descripcion_estado = msg or "RUC del CDC no coincide con dRucEm"
            doc_electronico.json_respuesta_api = resp
            doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
            doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
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
                doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
                doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])

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
            doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
            doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
            return {"status": "error", "detail": "RUC CDC != dRucEm"}

        # Otros errores: marcamos y reintentamos
        doc_electronico.estado_sifen = "error_api"
        doc_electronico.descripcion_estado = f"Error al consultar estado: {error_desc}"
        doc_electronico.json_respuesta_api = resp
        doc_electronico.fecha_ultimo_cambio_estado = timezone.now()
        doc_electronico.save(update_fields=["estado_sifen", "descripcion_estado", "json_respuesta_api", "fecha_ultimo_cambio_estado"])
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
                d.fecha_ultimo_cambio_estado = timezone.now()
                d.save(update_fields=["estado_sifen", "descripcion_estado", "fecha_ultimo_cambio_estado"])
            return {"status": "error", "detail": "RUC CDC != dRucEm"}
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            d = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if d:
                d.estado_sifen = "error_api"
                d.descripcion_estado = f"Fallo persistente al consultar estado SIFEN: {e}"
                d.fecha_ultimo_cambio_estado = timezone.now()
                d.save(update_fields=["estado_sifen", "descripcion_estado", "fecha_ultimo_cambio_estado"])
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
            doc.save()
            return {"status": "success", "estado": "cancelado"}

        resp = client.solicitar_cancelacion(doc.cdc, emisor.ruc)
        if resp.get("code", -1) == 0:
            doc.estado_sifen = "pendiente_cancelacion"
            doc.descripcion_estado = "Solicitud de cancelación enviada."
            doc.json_respuesta_api = resp
            doc.save()
            get_estado_sifen_task.apply_async((doc.id,), countdown=60)
            return {"status": "success", "estado": "solicitud_enviada"}

        err = resp.get("description", "Error desconocido al solicitar cancelación")
        doc.descripcion_estado = f"Error al solicitar cancelación: {err}"
        doc.json_respuesta_api = resp
        doc.save()
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
                d.save()
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
            doc.save()
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
            doc.save()
            get_estado_sifen_task.apply_async((doc.id,), countdown=60)
            return {"status": "success", "estado": "solicitud_enviada"}

        err = resp.get("description", "Error desconocido al solicitar inutilización")
        doc.descripcion_estado = f"Error al solicitar inutilización: {err}"
        doc.json_respuesta_api = resp
        doc.save()
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
                d.save()
            return {"status": "failed", "error": str(e)}
