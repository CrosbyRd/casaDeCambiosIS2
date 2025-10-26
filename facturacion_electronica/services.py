import os
import uuid
import requests
import decimal # Importar el módulo decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico  # noqa
from transacciones.models import Transaccion  # noqa  # Asumiendo que Transaccion está en la app transacciones


class FacturaSeguraAPIClient:
    """
    Cliente de la API de Factura Segura con:
    - Modo simulación (sin pegar a la red, útil en DEBUG).
    - Login con persistencia de token en Emisor.
    - Reintento automático ante 401 (token expirado).
    - Descarga binaria (PDF/XML) cuando se pide.
    - Respeto del rango de numeración (401–450) en generar_de().
    - Flujo 'contrato estricto' de la API (params={"DE": ...}) por defecto.
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
        # Permite forzar el modo estricto del contrato del API
        self.strict_contract = cfg.get("STRICT_CONTRACT", True)

        self.session = requests.Session()

    # ---------------------------
    # Autenticación
    # ---------------------------

    def _get_auth_token(self) -> str:
        # Usa el token guardado; si no hay, genera uno y lo persiste
        if self.emisor.auth_token:
            return self.emisor.auth_token
        return self._generate_auth_token()

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
        token = data["response"]["user"]["authentication_token"]

        self.emisor.auth_token = token
        self.emisor.token_generado_at = timezone.now()
        self.emisor.save(update_fields=["auth_token", "token_generado_at"])
        return token

    # ---------------------------
    # Core request (con simulación y refresh de token)
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

        import json
        print(f"DEBUG: [FacturaSeguraAPI - SIMULACION] JSON de entrada para '{operation}': {json.dumps(params, indent=2)}")

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
            de_resumido = params.get("DE", {}) or {}
            # Aquí simulamos los cálculos que haría la API real
            # Para esto, podemos usar una versión simplificada de _build_de_resumido_desde_transaccion
            # o simplemente devolver un JSON con algunos campos calculados de ejemplo.
            # Para una simulación más útil, intentaremos replicar algunos cálculos básicos.
            
            # Nota: Para una simulación completa y precisa, necesitaríamos replicar toda la lógica
            # de cálculo de SIFEN, lo cual es complejo. Aquí haremos una aproximación.
            
            # Copiamos el DE resumido y añadimos algunos campos calculados
            simulated_de_completo = de_resumido.copy()
            
            # Ejemplo de cómo podrías simular algunos cálculos si tuvieras la lógica aquí
            # Para este caso, simplemente devolveremos el mismo JSON de entrada, pero
            # en un escenario real, aquí se aplicarían las reglas de cálculo de SIFEN.
            # Dado que el objetivo es "ver el JSON", devolver el input es un buen primer paso.
            
            # Sin embargo, para que sea más útil, podemos intentar simular los totales
            # basándonos en los ítems si están presentes.
            
            total_ope_items = decimal.Decimal("0")
            total_iva_items = decimal.Decimal("0")
            
            for item in simulated_de_completo.get("gCamItem", []):
                try:
                    cant = decimal.Decimal(item.get("dCantProSer", "0"))
                    precio = decimal.Decimal(item.get("dPUniProSer", "0"))
                    desc = decimal.Decimal(item.get("dDescItem", "0"))
                    
                    item_total = (precio - desc) * cant
                    total_ope_items += item_total
                    
                    # Simulación básica de IVA (asumiendo 10% para gravados)
                    if item.get("iAfecIVA") == "1" and item.get("dTasaIVA") == "10":
                        total_iva_items += item_total / decimal.Decimal("11") * decimal.Decimal("1") # 10% IVA
                    elif item.get("iAfecIVA") == "1" and item.get("dTasaIVA") == "5":
                        total_iva_items += item_total / decimal.Decimal("21") * decimal.Decimal("1") # 5% IVA
                        
                except Exception:
                    pass # Ignorar errores en ítems simulados
            
            simulated_de_completo["dTotOpe"] = str(total_ope_items.normalize())
            simulated_de_completo["dTotGralOpe"] = str(total_ope_items.normalize())
            simulated_de_completo["dTotIVA"] = str(total_iva_items.normalize())
            
            # Añadir otros campos calculados que la API de Factura Segura devolvería
            # Estos son solo ejemplos, la lista completa está en la documentación
            simulated_de_completo["dSubExe"] = simulated_de_completo.get("dSubExe", "0")
            simulated_de_completo["dSubExo"] = simulated_de_completo.get("dSubExo", "0")
            simulated_de_completo["dSub5"] = simulated_de_completo.get("dSub5", "0")
            simulated_de_completo["dSub10"] = simulated_de_completo.get("dSub10", "0")
            simulated_de_completo["dTotDesc"] = simulated_de_completo.get("dTotDesc", "0")
            simulated_de_completo["dIVA5"] = simulated_de_completo.get("dIVA5", "0")
            simulated_de_completo["dIVA10"] = simulated_de_completo.get("dIVA10", "0")
            simulated_de_completo["dBaseGrav5"] = simulated_de_completo.get("dBaseGrav5", "0")
            simulated_de_completo["dBaseGrav10"] = simulated_de_completo.get("dBaseGrav10", "0")
            simulated_de_completo["dTBasGraIVA"] = simulated_de_completo.get("dTBasGraIVA", "0")
            
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [{"DE": simulated_de_completo}],
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

    def _make_request(self, operation: str, params: dict, *, is_file: bool = False):
        """
        Envía la operación al endpoint ESI con header Authentication-Token.
        - Si simulation_mode: retorna respuesta simulada.
        - Si 401: regenera token y reintenta 1 vez.
        """
        if self.simulation_mode:
            return self._simulate_api_response(operation, params, is_file=is_file)

        token = self._get_auth_token()
        payload = {"operation": operation, "params": params or {}}
        headers = {
            "Authentication-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            import json
            print(f"DEBUG: [FacturaSeguraAPI] Enviando a {self.base_url_esi} (Operación: {operation}): {json.dumps(payload, indent=2)}")
            resp = self.session.post(self.base_url_esi, json=payload, headers=headers, timeout=self.timeout)
            print(f"DEBUG: [FacturaSeguraAPI] Respuesta de {self.base_url_esi} (Operación: {operation}) - Status: {resp.status_code}, Contenido: {resp.text}")
            if resp.status_code == 401:
                # Token inválido/expirado -> refrescar y reintentar 1 vez
                self.emisor.auth_token = ""
                self.emisor.save(update_fields=["auth_token"])
                token = self._generate_auth_token()
                headers["Authentication-Token"] = token
                print(f"DEBUG: [FacturaSeguraAPI] Reintentando con nuevo token. Enviando a {self.base_url_esi} (Operación: {operation}): {json.dumps(payload, indent=2)}")
                resp = self.session.post(self.base_url_esi, json=payload, headers=headers, timeout=self.timeout)
                print(f"DEBUG: [FacturaSeguraAPI] Respuesta de reintento de {self.base_url_esi} (Operación: {operation}) - Status: {resp.status_code}, Contenido: {resp.text}")

            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            detail_text = getattr(e.response, "text", str(e))
            try:
                detail_json = e.response.json()
            except Exception:
                detail_json = None
            # Puedes agregar logging aquí si lo deseas
            raise requests.HTTPError(f"HTTP {e.response.status_code if e.response else ''} en {operation}: {detail_text}") from e

    # ---------------------------
    # Operaciones DE
    # ---------------------------

    def calcular_de(self, json_resumido_de: dict):
        """
        Llama a 'calcular_de': recibe DE resumido y devuelve DE con cálculos.
        (Contrato estricto: params={"DE": ...})
        """
        params = {"DE": json_resumido_de}
        return self._make_request("calcular_de", params)

    @transaction.atomic
    def generar_de(self, json_de_completo: dict, transaccion_id=None):
        """
        Llama a 'generar_de' para crear el DE en FacturaSegura.
        - Asigna dNumDoc dentro del rango 401–450 (con lock de fila).
        - Inyecta datos del emisor según XML del profe si faltan.
        - Crea DocumentoElectronico local con la respuesta (CDC/estado).
        - Modo estricto por defecto: params={"DE": json_de_completo}
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
        json_de_completo.setdefault("dEst", emisor_instance.establecimiento or "001")
        json_de_completo.setdefault("dPunExp", emisor_instance.punto_expedicion or "003")
        if emisor_instance.numero_timbrado_actual:
            json_de_completo.setdefault("dNumTim", emisor_instance.numero_timbrado_actual)
        if emisor_instance.fecha_inicio_timbrado:
            json_de_completo.setdefault("dFeIniT", emisor_instance.fecha_inicio_timbrado.strftime("%Y-%m-%d"))

        # ------ CONTRATO ESTRICTO (por defecto) ------
        params = {"DE": json_de_completo}

        response = self._make_request("generar_de", params)

        if response.get("code") == 0:
            # Éxito
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
                json_enviado_api={"operation": "generar_de", "params": params},
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
            json_enviado_api={"operation": "generar_de", "params": params},
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

    # --- INICIO: flujo contrato estricto utilitario ---

    def calcular_de_contrato_estricto(self, de_resumido: dict) -> dict:
        """
        Llama a operation=calcular_de cumpliendo el contrato del API:
        params = {"DE": <JSON_RESUMIDO_DE>}
        Retorna el JSON_DE completo que viene en results[0]["DE"].
        """
        payload_params = {"DE": de_resumido}
        resp = self._make_request("calcular_de", payload_params)
        code = resp.get("code", -1)
        if code < 0:
            raise RuntimeError(f"Error calcular_de: {resp.get('description')} | {resp}")
        results = resp.get("results") or []
        if not results or "DE" not in results[0]:
            raise RuntimeError(f"Respuesta calcular_de sin DE: {resp}")
        return results[0]["DE"]

    def generar_de_contrato_estricto(self, de_completo: dict) -> str:
        """
        Llama a operation=generar_de cumpliendo el contrato del API:
        params = {"DE": <JSON_DE>}
        Retorna el CDC (results[0]["CDC"]).
        """
        payload_params = {"DE": de_completo}
        resp = self._make_request("generar_de", payload_params)
        code = resp.get("code", -1)
        if code < 0:
            # Propaga la descripción exacta (p.ej. -80001 ESI sin permiso)
            raise RuntimeError(f"Error generar_de: {resp.get('description')} | {resp}")
        results = resp.get("results") or []
        if not results or "CDC" not in results[0]:
            raise RuntimeError(f"Respuesta generar_de sin CDC: {resp}")
        return results[0]["CDC"]

    def emitir_end_to_end_contrato_estricto(self, de_resumido: dict) -> dict:
        """
        Pipeline recomendado por el doc de la API:
        1) calcular_de -> devuelve DE completo
        2) generar_de -> devuelve CDC
        Retorna dict con {"cdc": ..., "de": ...} para que lo guardes en BD.
        """
        de_completo = self.calcular_de_contrato_estricto(de_resumido)
        cdc = self.generar_de_contrato_estricto(de_completo)
        return {"cdc": cdc, "de": de_completo}

    # --- FIN: flujo contrato estricto utilitario ---

    def calcular_de_contrato_estricto(self, de_resumido: dict) -> dict:
        payload_params = {"DE": de_resumido}
        resp = self._make_request("calcular_de", payload_params)
        code = resp.get("code", -1)
        if code < 0:
            raise RuntimeError(f"Error calcular_de: {resp.get('description')} | {resp}")
        results = resp.get("results") or []
        if not results or "DE" not in results[0]:
            raise RuntimeError(f"Respuesta calcular_de sin DE: {resp}")
        return results[0]["DE"]

    def generar_de_contrato_estricto(self, de_completo: dict) -> str:
        payload_params = {"DE": de_completo}
        resp = self._make_request("generar_de", payload_params)
        code = resp.get("code", -1)
        if code < 0:
            raise RuntimeError(f"Error generar_de: {resp.get('description')} | {resp}")
        results = resp.get("results") or []
        if not results or "CDC" not in results[0]:
            raise RuntimeError(f"Respuesta generar_de sin CDC: {resp}")
        return results[0]["CDC"]

    def emitir_end_to_end_contrato_estricto(self, de_resumido: dict) -> dict:
        de_completo = self.calcular_de_contrato_estricto(de_resumido)
        cdc = self.generar_de_contrato_estricto(de_completo)
        return {"cdc": cdc, "de": de_completo}
