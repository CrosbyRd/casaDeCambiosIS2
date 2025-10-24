import os
import uuid
import requests
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico  # noqa
from transacciones.models import Transaccion  # noqa  # Asumiendo que Transaccion está en la app transacciones


class FacturaSeguraAPIClient:
    """
    Cliente de la API de Factura Segura con:
    - Modo simulación (sinpega a la red, útil en DEBUG).
    - Login con persistencia de token en Emisor.
    - Reintento automático ante 401 (token expirado).
    - Descarga binaria (PDF/XML) cuando se pide.
    - Respeto del rango de numeración (401–450) en generar_de().
    """

    def __init__(self, emisor_id: int):
        self.emisor = EmisorFacturaElectronica.objects.get(id=emisor_id)

        cfg = getattr(settings, "FACTURASEGURA", {})
        # BASE apuntando ya a /misife00/v1/esi
        self.base_url_esi = (cfg.get("BASE_URL") or "").rstrip("/")
        self.login_url = cfg.get("LOGIN_URL")
        self.timeout = cfg.get("TIMEOUT", 30)
        self.retries = cfg.get("RETRIES", 3)
        self.simulation_mode = cfg.get("SIMULATION_MODE", True)

        self.session = requests.Session()

    # ---------------------------
    # Autenticación
    # ---------------------------

    def _get_auth_token(self):
        # Usa el token guardado; si no hay, genera uno y lo persiste
        if self.emisor.auth_token:
            return self.emisor.auth_token
        return self._generate_auth_token()

    def _make_request(self, operation: str, params: dict):
        token = self._get_auth_token()
        payload = {"operation": operation, "params": params or {}}
        headers = {
            "Authentication-Token": token,
            "Content-Type": "application/json",
        }
        resp = self.session.post(self.base_url_esi, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _generate_auth_token(self) -> str:
        """
        Genera un nuevo token de autenticación para el ESI y lo persiste en el Emisor.
        """
        if self.simulation_mode:
            fake_token = "SIMULATED_AUTH_TOKEN_" + os.urandom(16).hex()
            self.emisor.auth_token = fake_token
            self.emisor.token_generado_at = timezone.now()
            self.emisor.save(update_fields=["auth_token", "token_generado_at"])
            return fake_token

        email = os.getenv("FACTURASEGURA_ESI_EMAIL") or getattr(settings, "FACTURASEGURA", {}).get("EMAIL")
        password = os.getenv("FACTURASEGURA_ESI_PASSWORD") or getattr(settings, "FACTURASEGURA", {}).get("PASSWORD")

        if not email or not password:
            raise ValueError("Credenciales del usuario ESI no configuradas (FACTURASEGURA_ESI_EMAIL/_PASSWORD o settings.FACTURASEGURA).")

        if not self.login_url:
            raise ValueError("URL de login de FacturaSegura no configurada (FACTURASEGURA_LOGIN_URL_* o settings.FACTURASEGURA['LOGIN_URL']).")

        headers = {"Content-Type": "application/json", "accept": "application/json"}
        payload = {"email": email, "password": password}

        resp = requests.post(self.login_url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # Adapta esta ruta si tu API devuelve el token en otro atributo:
        token = data["response"]["user"]["authentication_token"]

        self.emisor.auth_token = token
        self.emisor.token_generado_at = timezone.now()
        self.emisor.save(update_fields=["auth_token", "token_generado_at"])
        return token


    # ---------------------------
    # Simulación (DEV)
    # ---------------------------

    def _simulate_api_response(self, operation: str, params: dict, is_file: bool = False):
        """
        Simula la API de Factura Segura.
        - Para 'dwn_kude' retorna bytes tipo PDF.
        - Para 'dwn_xml' retorna bytes tipo XML.
        - Para 'generar_de' retorna CDC simulado.
        - Para 'get_estado_sifen' retorna 'Aprobado'.
        - Para 'calcular_de' re-eco del DE.
        """
        if operation == "dwn_kude" and is_file:
            # PDF mínimo simulado
            return b"%PDF-1.4\n% Simulado KuDE\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"

        if operation == "dwn_xml" and is_file:
            # XML mínimo simulado
            return b'<?xml version="1.0" encoding="UTF-8"?><DE Simulado="true"></DE>'

        if operation == "generar_de":
            fake_cdc = f"SIMULATED{uuid.uuid4().hex[:34].upper()}"
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [{"CDC": fake_cdc}],
            }

        if operation == "get_estado_sifen":
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [{
                    "estado_sifen": "Aprobado",
                    "desc_sifen": "0260 - Aprobado (Simulado)",
                    "error_sifen": "",
                    "fch_sifen": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado_can": "", "desc_can": "", "error_can": "", "fch_can": "",
                    "estado_inu": "", "desc_inu": "", "error_inu": "", "fch_inu": "",
                }],
            }

        if operation == "calcular_de":
            de_json = params.get("DE", {}) or {}
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [{"DE": de_json}],
            }

        if operation in ["sol_cancelacion", "sol_inutilizacion"]:
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [],
            }

        return {
            "code": -9999,
            "description": f"Operación '{operation}' no simulada.",
            "operation_info": {"id": str(uuid.uuid4())},
            "results": [],
        }

    # ---------------------------
    # Operaciones DE
    # ---------------------------

    def calcular_de(self, json_resumido_de: dict):
        """
        Llama a 'calcular_de': recibe DE resumido y devuelve DE con cálculos.
        """
        params = {"DE": json_resumido_de}
        return self._make_request("calcular_de", params)

    @transaction.atomic
    def generar_de(self, json_de_completo: dict, transaccion_id=None):
        """
        Llama a 'generar_de' para crear el DE en FacturaSegura.
        - Asigna dNumDoc dentro del rango 401–450 (con lock de fila).
        - Inyecta datos del emisor según XML del profe.
        - Crea DocumentoElectronico local con la respuesta (CDC/estado).
        """
        emisor_instance = EmisorFacturaElectronica.objects.select_for_update().get(id=self.emisor.id)

        # Validar/normalizar correlativo
        if emisor_instance.siguiente_numero_factura is None:
            emisor_instance.siguiente_numero_factura = emisor_instance.rango_numeracion_inicio

        if not (emisor_instance.rango_numeracion_inicio <= emisor_instance.siguiente_numero_factura <= emisor_instance.rango_numeracion_fin):
            raise ValueError("Rango agotado o inválido para emisión de factura.")

        numero_doc_int = emisor_instance.siguiente_numero_factura
        numero_doc_str = f"{numero_doc_int:07d}"

        # Inyectar numeración y datos del emisor (respetando claves del XML)
        json_de_completo.setdefault("dNumDoc", numero_doc_str)
        json_de_completo.setdefault("dRucEm", emisor_instance.ruc)
        json_de_completo.setdefault("dDVEmi", emisor_instance.dv_ruc)
        json_de_completo.setdefault("dEst", emisor_instance.establecimiento)
        json_de_completo.setdefault("dPunExp", emisor_instance.punto_expedicion)
        if emisor_instance.numero_timbrado_actual:
            json_de_completo.setdefault("dNumTim", emisor_instance.numero_timbrado_actual)
        if emisor_instance.fecha_inicio_timbrado:
            json_de_completo.setdefault("dFeIniT", emisor_instance.fecha_inicio_timbrado.strftime("%Y-%m-%d"))

        params = {
            "dRucEm": emisor_instance.ruc,
            "dDVEmi": emisor_instance.dv_ruc,
            "dEst": emisor_instance.establecimiento,
            "dPunExp": emisor_instance.punto_expedicion,
            "dNumTim": emisor_instance.numero_timbrado_actual,
            "DE": json_de_completo,
        }

        response = self._make_request("generar_de", params)

        if response.get("code") == 0:
            # Éxito
            # Algunas APIs devuelven en results[0]['CDC'], otras en response['cdc']; mantenemos tu contrato
            results = response.get("results") or []
            cdc = (results[0].get("CDC") if results else None) or response.get("cdc")

            estado_sifen = "pendiente_aprobacion" if not self.simulation_mode else "simulado"
            descripcion_estado = response.get("description", "")

            doc_electronico = DocumentoElectronico.objects.create(
                emisor=emisor_instance,
                tipo_de="factura",
                numero_documento=numero_doc_str,
                numero_timbrado=json_de_completo.get("dNumTim"),
                cdc=cdc,
                estado_sifen=estado_sifen,
                descripcion_estado=descripcion_estado,
                json_enviado_api=json_de_completo,
                json_respuesta_api=response,
                transaccion_asociada_id=transaccion_id,
            )

            # Avanzar correlativo SOLO luego de éxito
            emisor_instance.siguiente_numero_factura = numero_doc_int + 1
            emisor_instance.save(update_fields=["siguiente_numero_factura"])

            return doc_electronico

        # Error API: registrar documento en estado error para auditoría
        DocumentoElectronico.objects.create(
            emisor=emisor_instance,
            tipo_de="factura",
            numero_documento=numero_doc_str,
            numero_timbrado=json_de_completo.get("dNumTim"),
            estado_sifen="error_api",
            descripcion_estado=response.get("description", "Error desconocido de la API"),
            json_enviado_api=json_de_completo,
            json_respuesta_api=response,
            transaccion_asociada_id=transaccion_id,
        )
        raise Exception(f"Error de API al generar DE: {response.get('description')}")

    def get_estado_sifen(self, cdc: str, ruc_emisor: str):
        """
        Consulta el estado SIFEN de un DE.
        """
        params = {"CDC": cdc, "dRucEm": ruc_emisor}
        return self._make_request("get_estado_sifen", params)

    def solicitar_cancelacion(self, cdc: str, ruc_emisor: str):
        """
        Solicita la cancelación de un DE.
        """
        params = {"CDC": cdc, "dRucEm": ruc_emisor}
        return self._make_request("sol_cancelacion", params)

    def solicitar_inutilizacion(self, ruc_emisor: str, tipo_de: str, num_timbrado: str, establecimiento: str, punto_exp: str, num_doc: str):
        """
        Solicita la inutilización de un número de DE.
        """
        params = {
            "dRucEm": ruc_emisor,
            "iTiDE": tipo_de,  # '1' Factura, '5' Nota de Crédito (ajusta si tu API usa otro código)
            "dNumTim": num_timbrado,
            "dEst": establecimiento,
            "dPunExp": punto_exp,
            "dNumDoc": num_doc,
        }
        return self._make_request("sol_inutilizacion", params)

    # ---------------------------
    # Descargas
    # ---------------------------

def descargar_kude(self, cdc: str, ruc_emisor: str) -> bytes:
    """
    Descarga el KuDE (PDF) con endpoint path-style:
    GET {BASE_URL}/dwn_kude/{dRucEm}/{CDC}
    """
    if self.simulation_mode:
        return b"%PDF-1.4\n% Simulado KuDE\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"

    token = self._get_auth_token()
    url = f"{self.base_url_esi}/dwn_kude/{ruc_emisor}/{cdc}"
    resp = self.session.get(url, headers={"Authentication-Token": token}, timeout=self.timeout)
    resp.raise_for_status()
    return resp.content

def descargar_xml(self, cdc: str, ruc_emisor: str) -> bytes:
    """
    Descarga el XML firmado con endpoint path-style:
    GET {BASE_URL}/dwn_xml/{dRucEm}/{CDC}
    """
    if self.simulation_mode:
        return b'<?xml version="1.0" encoding="UTF-8"?><DE Simulado="true"></DE>'

    token = self._get_auth_token()
    url = f"{self.base_url_esi}/dwn_xml/{ruc_emisor}/{cdc}"
    resp = self.session.get(url, headers={"Authentication-Token": token}, timeout=self.timeout)
    resp.raise_for_status()
    return resp.content

