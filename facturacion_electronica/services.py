import requests
import os
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico
from transacciones.models import Transaccion # Asumiendo que Transaccion está en la app transacciones

class FacturaSeguraAPIClient:
    def __init__(self, emisor_id):
        self.emisor = EmisorFacturaElectronica.objects.get(id=emisor_id)
        self.base_url_esi = os.getenv("FACTURASEGURA_API_URL_TEST") if settings.DEBUG else os.getenv("FACTURASEGURA_API_URL_PROD")
        self.login_url = os.getenv("FACTURASEGURA_LOGIN_URL_TEST") if settings.DEBUG else os.getenv("FACTURASEGURA_LOGIN_URL_PROD")
        self.simulation_mode = settings.FACTURASEGURA_SIMULATION_MODE # Controla si se llama a la API real

    def _get_auth_token(self):
        """
        Obtiene el token de autenticación. Si no existe o ha expirado (aunque la API dice que no expira,
        es buena práctica tener un mecanismo de re-generación si falla), lo genera.
        """
        # La API indica que el token es válido hasta que el usuario cambie la contraseña.
        # Por simplicidad, aquí solo verificamos si existe. Si la API retorna un error de auth,
        # se podría implementar una lógica para regenerarlo.
        if not self.emisor.auth_token:
            return self._generate_auth_token()
        return self.emisor.auth_token

    def _generate_auth_token(self):
        """
        Genera un nuevo token de autenticación para el ESI.
        """
        email = os.getenv("FACTURASEGURA_ESI_EMAIL")
        password = os.getenv("FACTURASEGURA_ESI_PASSWORD")

        if not email or not password:
            raise ValueError("Las credenciales del usuario ESI no están configuradas en las variables de entorno.")

        headers = {"Content-Type": "application/json"}
        payload = {"email": email, "password": password}

        try:
            response = requests.post(self.login_url, headers=headers, json=payload)
            response.raise_for_status() # Lanza una excepción para códigos de estado HTTP de error
            data = response.json()
            token = data["response"]["user"]["authentication_token"]
            
            self.emisor.auth_token = token
            self.emisor.token_generado_at = timezone.now()
            self.emisor.save()
            return token
        except requests.exceptions.RequestException as e:
            print(f"Error al generar el token de autenticación: {e}")
            raise

    def _make_request(self, operation, params, method='POST', is_file_download=False):
        """
        Método genérico para construir y enviar las peticiones HTTP a la API de Factura Segura.
        """
        if self.simulation_mode and not is_file_download:
            print(f"Modo simulación activo para operación: {operation}. No se realizará llamada real a la API.")
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
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error en la petición POST a la API ({operation}): {e}")
                raise
        elif method == 'GET' and is_file_download:
            # Para dwn_kude y dwn_xml, la URL es diferente
            # https://apitest.facturasegura.com.py/misife00/v1/esi/operation/dRucEm/CDC
            cdc = params.get("CDC")
            dRucEm = params.get("dRucEm")
            if not cdc or not dRucEm:
                raise ValueError("CDC y dRucEm son requeridos para descargar archivos.")
            
            download_url = f"{self.base_url_esi}/{operation}/{dRucEm}/{cdc}"
            try:
                response = requests.get(download_url, headers={'Authentication-Token': token})
                response.raise_for_status()
                return response.content # Retorna el contenido binario del archivo
            except requests.exceptions.RequestException as e:
                print(f"Error al descargar archivo ({operation}): {e}")
                raise
        else:
            raise ValueError(f"Método HTTP no soportado o uso incorrecto para {operation}")

    def _simulate_api_response(self, operation, params):
        """
        Simula una respuesta exitosa de la API de Factura Segura para desarrollo.
        """
        print(f"Simulando respuesta para operación: {operation}")
        if operation == "generar_de":
            # Generar un CDC ficticio para simulación
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
            # Retorna el mismo JSON resumido con algunos campos calculados ficticios
            de_json = params.get("DE", {})
            # Aquí se podría añadir lógica para "calcular" algunos campos si es necesario para pruebas
            de_json["dTotOpe"] = "1000000" # Ejemplo de campo calculado
            de_json["dIVA10"] = "90909" # Ejemplo
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
        Actualiza el siguiente número de factura del emisor.
        """
        emisor_instance = EmisorFacturaElectronica.objects.select_for_update().get(id=self.emisor.id)

        # Asignar el número de documento antes de llamar a la API (o simularlo)
        # Formatear a 7 dígitos con ceros a la izquierda
        numero_doc_str = str(emisor_instance.siguiente_numero_factura).zfill(7)
        json_de_completo["dNumDoc"] = numero_doc_str
        
        params = {"DE": json_de_completo}
        
        try:
            response = self._make_request("generar_de", params)

            if response["code"] == 0:
                cdc = response["results"][0]["CDC"]
                estado_sifen = 'pendiente_aprobacion' if not self.simulation_mode else 'simulado'
                descripcion_estado = response["description"]
                
                # Crear el DocumentoElectronico en la DB
                doc_electronico = DocumentoElectronico.objects.create(
                    emisor=emisor_instance,
                    tipo_de='factura', # Asumimos factura por ahora, se puede hacer dinámico
                    numero_documento=numero_doc_str,
                    numero_timbrado=json_de_completo.get("dNumTim"),
                    cdc=cdc,
                    estado_sifen=estado_sifen,
                    descripcion_estado=descripcion_estado,
                    json_enviado_api=json_de_completo,
                    json_respuesta_api=response,
                    transaccion_asociada_id=transaccion_id
                )

                # Incrementar el siguiente número de factura SOLO si la generación fue exitosa
                # y está dentro del rango.
                if emisor_instance.siguiente_numero_factura < emisor_instance.rango_numeracion_fin:
                    emisor_instance.siguiente_numero_factura += 1
                    emisor_instance.save()
                else:
                    print(f"Advertencia: El rango de numeración para {emisor_instance.email_equipo} está por agotarse.")

                return doc_electronico
            else:
                print(f"Error al generar DE: {response.get('description')}")
                # Aquí se podría guardar un DocumentoElectronico con estado de error
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
        except Exception as e:
            print(f"Excepción al generar DE: {e}")
            # Si ocurre una excepción antes de guardar el DocumentoElectronico,
            # se podría crear uno con estado de error aquí también.
            raise

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
            "iTiDE": tipo_de, # '1' para Factura, '5' para Nota de Crédito
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
