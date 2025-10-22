import requests
import os
import json
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico
from transacciones.models import Transaccion  # Asumiendo que Transaccion está en la app transacciones

class FacturaSeguraAPIClient:
    def __init__(self, emisor_id):
        self.emisor = EmisorFacturaElectronica.objects.get(id=emisor_id)
        self.base_url_esi = os.getenv("FACTURASEGURA_API_URL_TEST") if settings.DEBUG else os.getenv("FACTURASEGURA_API_URL_PROD")
        self.login_url = os.getenv("FACTURASEGURA_LOGIN_URL_TEST") if settings.DEBUG else os.getenv("FACTURASEGURA_LOGIN_URL_PROD")
        # Debes tener FACTURASEGURA_SIMULATION_MODE en settings.py
        self.simulation_mode = getattr(settings, "FACTURASEGURA_SIMULATION_MODE", True)

    def _get_auth_token(self):
        """
        Obtiene el token de autenticación. Si no existe lo genera.
        """
        if not self.emisor.auth_token:
            return self._generate_auth_token()
        return self.emisor.auth_token

    def _generate_auth_token(self):
        """
        Genera un nuevo token de autenticación para el ESI.
        """
        if self.simulation_mode:
            fake_token = "SIMULATED_AUTH_TOKEN_" + os.urandom(16).hex()
            self.emisor.auth_token = fake_token
            self.emisor.token_generado_at = timezone.now()
            self.emisor.save()
            return fake_token

        email = os.getenv("FACTURASEGURA_ESI_EMAIL")
        password = os.getenv("FACTURASEGURA_ESI_PASSWORD")

        if not email or not password:
            raise ValueError("Las credenciales del usuario ESI no están configuradas en las variables de entorno.")

        headers = {"Content-Type": "application/json"}
        payload = {"email": email, "password": password}

        response = requests.post(self.login_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        token = data["response"]["user"]["authentication_token"]

        self.emisor.auth_token = token
        self.emisor.token_generado_at = timezone.now()
        self.emisor.save()
        return token

    def _make_request(self, operation, params, method='POST', is_file_download=False):
        """
        Método genérico para construir y enviar las peticiones HTTP a la API de Factura Segura.
        """
        if self.simulation_mode and not is_file_download:
            return self._simulate_api_response(operation, params)

        token = self._get_auth_token()
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'Authentication-Token': token
        }

        url = self.base_url_esi

        if method == 'POST':
            payload = {"operation": operation, "params": params}
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        elif method == 'GET' and is_file_download:
            # Para dwn_kude y dwn_xml:
            # https://.../misife00/v1/esi/{operation}/{dRucEm}/{CDC}
            cdc = params.get("CDC")
            dRucEm = params.get("dRucEm")
            if not cdc or not dRucEm:
                raise ValueError("CDC y dRucEm son requeridos para descargar archivos.")
            download_url = f"{self.base_url_esi}/{operation}/{dRucEm}/{cdc}"
            response = requests.get(download_url, headers={'Authentication-Token': token})
            response.raise_for_status()
            return response.content
        else:
            raise ValueError(f"Método HTTP no soportado o uso incorrecto para {operation}")

    def _simulate_api_response(self, operation, params):
        """
        Simula una respuesta exitosa de la API de Factura Segura para desarrollo.
        """
        if operation == "generar_de":
            fake_cdc = f"SIMULATED{uuid.uuid4().hex[:34].upper()}"
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [{"CDC": fake_cdc}]
            }
        elif operation == "get_estado_sifen":
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
                    "estado_inu": "", "desc_inu": "", "error_inu": "", "fch_inu": ""
                }]
            }
        elif operation == "calcular_de":
            de_json = params.get("DE", {})
            # Puedes "calcular" algunos campos de prueba si lo deseas
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": [{"DE": de_json}]
            }
        elif operation in ["sol_cancelacion", "sol_inutilizacion"]:
            return {
                "code": 0,
                "description": "OK (Simulado)",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": []
            }
        else:
            return {
                "code": -9999,
                "description": f"Operación '{operation}' no simulada.",
                "operation_info": {"id": str(uuid.uuid4())},
                "results": []
            }

    def calcular_de(self, json_resumido_de):
        """
        Llama a la operación 'calcular_de' de la API.
        Recibe un JSON resumido y retorna el JSON con campos calculados.
        """
        params = {"DE": json_resumido_de}
        return self._make_request("calcular_de", params)

    @transaction.atomic
    def generar_de(self, json_de_completo, transaccion_id=None):
        """
        Llama a la operación 'generar_de' de la API para generar un documento electrónico.
        Asigna dNumDoc del rango y completa datos del emisor antes de enviar.
        """
        emisor_instance = EmisorFacturaElectronica.objects.select_for_update().get(id=self.emisor.id)

        # Validar rango antes de asignar número
        if emisor_instance.siguiente_numero_factura is None:
            emisor_instance.siguiente_numero_factura = emisor_instance.rango_numeracion_inicio

        if emisor_instance.siguiente_numero_factura < emisor_instance.rango_numeracion_inicio or emisor_instance.siguiente_numero_factura > emisor_instance.rango_numeracion_fin:
            raise ValueError("Rango agotado o inválido para emisión de factura.")

        numero_doc_str = str(emisor_instance.siguiente_numero_factura).zfill(7)
        json_de_completo["dNumDoc"] = numero_doc_str

        # Inyectar datos del emisor en el DE
        json_de_completo.setdefault("dRucEm", emisor_instance.ruc)
        json_de_completo.setdefault("dDVEmi", emisor_instance.dv_ruc)
        json_de_completo.setdefault("dEst", emisor_instance.establecimiento)
        json_de_completo.setdefault("dPunExp", emisor_instance.punto_expedicion)
        if emisor_instance.numero_timbrado_actual:
            json_de_completo.setdefault("dNumTim", emisor_instance.numero_timbrado_actual)
        if emisor_instance.fecha_inicio_timbrado:
            json_de_completo.setdefault("dFeIniT", emisor_instance.fecha_inicio_timbrado.strftime("%Y-%m-%d"))

        params = {"DE": json_de_completo}
        response = self._make_request("generar_de", params)

        if response["code"] == 0:
            cdc = response["results"][0]["CDC"]
            estado_sifen = 'pendiente_aprobacion' if not self.simulation_mode else 'simulado'
            descripcion_estado = response.get("description", "")

            doc_electronico = DocumentoElectronico.objects.create(
                emisor=emisor_instance,
                tipo_de='factura',
                numero_documento=numero_doc_str,
                numero_timbrado=json_de_completo.get("dNumTim"),
                cdc=cdc,
                estado_sifen=estado_sifen,
                descripcion_estado=descripcion_estado,
                json_enviado_api=json_de_completo,
                json_respuesta_api=response,
                transaccion_asociada_id=transaccion_id
            )

            # Incrementar SIEMPRE tras uso exitoso del número
            emisor_instance.siguiente_numero_factura = emisor_instance.siguiente_numero_factura + 1
            emisor_instance.save(update_fields=["siguiente_numero_factura"])

            return doc_electronico
        else:
            # Guardar documento con error para auditoría
            DocumentoElectronico.objects.create(
                emisor=emisor_instance,
                tipo_de='factura',
                numero_documento=numero_doc_str,
                numero_timbrado=json_de_completo.get("dNumTim"),
                estado_sifen='error_api',
                descripcion_estado=response.get('description', 'Error desconocido de la API'),
                json_enviado_api=json_de_completo,
                json_respuesta_api=response,
                transaccion_asociada_id=transaccion_id
            )
            raise Exception(f"Error de API al generar DE: {response.get('description')}")

    def get_estado_sifen(self, cdc, ruc_emisor):
        """
        Consulta el estado de un documento electrónico en SIFEN.
        """
        params = {"CDC": cdc, "dRucEm": ruc_emisor}
        return self._make_request("get_estado_sifen", params)

    def solicitar_cancelacion(self, cdc, ruc_emisor):
        """
        Solicita la cancelación de un documento electrónico.
        """
        params = {"CDC": cdc, "dRucEm": ruc_emisor}
        return self._make_request("sol_cancelacion", params)

    def solicitar_inutilizacion(self, ruc_emisor, tipo_de, num_timbrado, establecimiento, punto_exp, num_doc):
        """
        Solicita la inutilización de un número de documento electrónico.
        """
        params = {
            "dRucEm": ruc_emisor,
            "iTiDE": tipo_de,  # '1' para Factura, '5' para Nota de Crédito
            "dNumTim": num_timbrado,
            "dEst": establecimiento,
            "dPunExp": punto_exp,
            "dNumDoc": num_doc
        }
        return self._make_request("sol_inutilizacion", params)

    def descargar_kude(self, cdc, ruc_emisor):
        """
        Descarga el KuDE en PDF.
        """
        params = {"CDC": cdc, "dRucEm": ruc_emisor}
        return self._make_request("dwn_kude", params, method='GET', is_file_download=True)

    def descargar_xml(self, cdc, ruc_emisor):
        """
        Descarga el XML firmado.
        """
        params = {"CDC": cdc, "dRucEm": ruc_emisor}
        return self._make_request("dwn_xml", params, method='GET', is_file_download=True)
