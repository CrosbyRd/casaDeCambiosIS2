from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .services import FacturaSeguraAPIClient
from .models import DocumentoElectronico, EmisorFacturaElectronica
import json
import time

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def generar_factura_electronica_task(self, emisor_id, transaccion_id, json_de_completo):
    """
    Tarea Celery para generar una factura electrónica a través de la API de Factura Segura.
    """
    try:
        client = FacturaSeguraAPIClient(emisor_id)
        doc_electronico = client.generar_de(json_de_completo, transaccion_id)
        
        # Si la generación fue exitosa y no estamos en modo simulación, programar la consulta de estado
        if doc_electronico and doc_electronico.estado_sifen != 'simulado':
            # Consultar el estado después de 1 minuto, como sugiere la API
            get_estado_sifen_task.apply_async(
                (doc_electronico.id,), 
                countdown=60 # 1 minuto
            )
        return {"status": "success", "cdc": doc_electronico.cdc if doc_electronico else None}
    except Exception as e:
        print(f"Error en generar_factura_electronica_task para transacción {transaccion_id}: {e}")
        # Reintentar la tarea en caso de fallo
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # Si se exceden los reintentos, marcar el documento como error_api si existe
            doc = DocumentoElectronico.objects.filter(transaccion_asociada_id=transaccion_id).first()
            if doc:
                doc.estado_sifen = 'error_api'
                doc.descripcion_estado = f"Fallo persistente al generar DE: {e}"
                doc.save()
            return {"status": "failed", "error": str(e)}

@shared_task(bind=True, max_retries=10, default_retry_delay=300) # Reintentar cada 5 minutos
def get_estado_sifen_task(self, documento_electronico_id):
    """
    Tarea Celery para consultar el estado de un documento electrónico en SIFEN.
    """
    try:
        doc_electronico = DocumentoElectronico.objects.get(id=documento_electronico_id)
        emisor = doc_electronico.emisor
        client = FacturaSeguraAPIClient(emisor.id)

        if client.simulation_mode:
            print(f"Modo simulación activo. No se consultará el estado SIFEN real para DE {documento_electronico_id}.")
            # Simular un cambio de estado si es necesario para pruebas
            if doc_electronico.estado_sifen == 'pendiente_aprobacion':
                doc_electronico.estado_sifen = 'simulado'
                doc_electronico.descripcion_estado = 'Estado simulado: Aprobado'
                doc_electronico.save()
            return {"status": "success", "estado": doc_electronico.estado_sifen}

        response = client.get_estado_sifen(doc_electronico.cdc, emisor.ruc)

        if response["code"] == 0 and response["results"]:
            sifen_data = response["results"][0]
            
            # Lógica para interpretar los estados de SIFEN según el documento de la API
            new_estado = doc_electronico.estado_sifen
            new_desc = doc_electronico.descripcion_estado

            if sifen_data.get("estado_inu") == "Aprobado":
                new_estado = 'inutilizado'
                new_desc = "Documento Inutilizado en SIFEN."
            elif sifen_data.get("estado_can") == "Aprobado":
                new_estado = 'cancelado'
                new_desc = "Documento Cancelado en SIFEN."
            elif sifen_data.get("estado_sifen") == "Aprobado":
                new_estado = 'aprobado'
                new_desc = sifen_data.get("desc_sifen", "Aprobado en SIFEN.")
            elif sifen_data.get("estado_sifen") == "Aprobado con observación":
                new_estado = 'aprobado_obs'
                new_desc = sifen_data.get("desc_sifen", "Aprobado con Observación en SIFEN.")
            elif sifen_data.get("estado_sifen") == "Rechazado":
                new_estado = 'rechazado'
                new_desc = sifen_data.get("desc_sifen", "Rechazado por SIFEN.")
            elif sifen_data.get("estado_sifen") in ["ERROR_SIFEN", "ERROR_ENVIO_LOTE", "REINTENTAR_LOTE", "ERROR_CONSULTA_LOTE"]:
                new_estado = 'error_sifen'
                new_desc = sifen_data.get("desc_sifen", "Error SIFEN.") + " " + sifen_data.get("error_sifen", "")
            elif sifen_data.get("estado_sifen") == "SOL.APROBACION":
                new_estado = 'pendiente_aprobacion'
                new_desc = "Solicitud de Aprobación en proceso."
            elif sifen_data.get("estado_sifen") == "ENVIADO_A_SIFEN":
                new_estado = 'pendiente_aprobacion' # O un estado intermedio si se desea
                new_desc = "Enviado a SIFEN, esperando respuesta."
            
            if new_estado != doc_electronico.estado_sifen:
                doc_electronico.estado_sifen = new_estado
                doc_electronico.descripcion_estado = new_desc
                doc_electronico.json_respuesta_api = response # Guardar la última respuesta de estado
                doc_electronico.save()
                print(f"Estado de DE {documento_electronico_id} actualizado a: {new_estado}")
            else:
                print(f"Estado de DE {documento_electronico_id} no ha cambiado: {new_estado}")

            # Si el estado aún no es final, programar otra consulta
            if new_estado not in ['aprobado', 'aprobado_obs', 'rechazado', 'cancelado', 'inutilizado', 'error_sifen']:
                self.retry(countdown=300) # Reintentar en 5 minutos
            
            return {"status": "success", "estado": new_estado}
        else:
            error_desc = response.get('description', 'Error desconocido al consultar estado')
            print(f"Error al consultar estado SIFEN para DE {documento_electronico_id}: {error_desc}")
            doc_electronico.estado_sifen = 'error_api'
            doc_electronico.descripcion_estado = f"Error al consultar estado: {error_desc}"
            doc_electronico.json_respuesta_api = response
            doc_electronico.save()
            self.retry(exc=Exception(error_desc)) # Reintentar en caso de error de la API

    except DocumentoElectronico.DoesNotExist:
        print(f"DocumentoElectronico con ID {documento_electronico_id} no encontrado.")
        return {"status": "failed", "error": "Documento no encontrado"}
    except Exception as e:
        print(f"Excepción en get_estado_sifen_task para DE {documento_electronico_id}: {e}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            doc = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if doc:
                doc.estado_sifen = 'error_api'
                doc.descripcion_estado = f"Fallo persistente al consultar estado SIFEN: {e}"
                doc.save()
            return {"status": "failed", "error": str(e)}

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def solicitar_cancelacion_task(self, documento_electronico_id):
    """
    Tarea Celery para solicitar la cancelación de un documento electrónico.
    """
    try:
        doc_electronico = DocumentoElectronico.objects.get(id=documento_electronico_id)
        emisor = doc_electronico.emisor
        client = FacturaSeguraAPIClient(emisor.id)

        if client.simulation_mode:
            print(f"Modo simulación activo. No se solicitará cancelación real para DE {documento_electronico_id}.")
            doc_electronico.estado_sifen = 'cancelado'
            doc_electronico.descripcion_estado = 'Cancelación simulada'
            doc_electronico.save()
            return {"status": "success", "estado": "cancelado"}

        response = client.solicitar_cancelacion(doc_electronico.cdc, emisor.ruc)
        if response["code"] == 0:
            doc_electronico.estado_sifen = 'pendiente_cancelacion' # Nuevo estado intermedio si se desea
            doc_electronico.descripcion_estado = "Solicitud de cancelación enviada."
            doc_electronico.json_respuesta_api = response
            doc_electronico.save()
            # Programar consulta de estado para verificar la cancelación
            get_estado_sifen_task.apply_async((doc_electronico.id,), countdown=60)
            return {"status": "success", "estado": "solicitud_enviada"}
        else:
            error_desc = response.get('description', 'Error desconocido al solicitar cancelación')
            doc_electronico.descripcion_estado = f"Error al solicitar cancelación: {error_desc}"
            doc_electronico.json_respuesta_api = response
            doc_electronico.save()
            raise Exception(f"Error de API al solicitar cancelación: {error_desc}")
    except DocumentoElectronico.DoesNotExist:
        print(f"DocumentoElectronico con ID {documento_electronico_id} no encontrado.")
        return {"status": "failed", "error": "Documento no encontrado"}
    except Exception as e:
        print(f"Excepción en solicitar_cancelacion_task para DE {documento_electronico_id}: {e}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            doc = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if doc:
                doc.estado_sifen = 'error_api'
                doc.descripcion_estado = f"Fallo persistente al solicitar cancelación: {e}"
                doc.save()
            return {"status": "failed", "error": str(e)}

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def solicitar_inutilizacion_task(self, documento_electronico_id):
    """
    Tarea Celery para solicitar la inutilización de un número de documento electrónico.
    """
    try:
        doc_electronico = DocumentoElectronico.objects.get(id=documento_electronico_id)
        emisor = doc_electronico.emisor
        client = FacturaSeguraAPIClient(emisor.id)

        if client.simulation_mode:
            print(f"Modo simulación activo. No se solicitará inutilización real para DE {documento_electronico_id}.")
            doc_electronico.estado_sifen = 'inutilizado'
            doc_electronico.descripcion_estado = 'Inutilización simulada'
            doc_electronico.save()
            return {"status": "success", "estado": "inutilizado"}

        response = client.solicitar_inutilizacion(
            ruc_emisor=emisor.ruc,
            tipo_de='1', # Asumimos factura, se puede hacer dinámico
            num_timbrado=doc_electronico.numero_timbrado,
            establecimiento=emisor.establecimiento,
            punto_exp=emisor.punto_expedicion,
            num_doc=doc_electronico.numero_documento
        )
        if response["code"] == 0:
            doc_electronico.estado_sifen = 'pendiente_inutilizacion' # Nuevo estado intermedio
            doc_electronico.descripcion_estado = "Solicitud de inutilización enviada."
            doc_electronico.json_respuesta_api = response
            doc_electronico.save()
            # Programar consulta de estado para verificar la inutilización
            get_estado_sifen_task.apply_async((doc_electronico.id,), countdown=60)
            return {"status": "success", "estado": "solicitud_enviada"}
        else:
            error_desc = response.get('description', 'Error desconocido al solicitar inutilización')
            doc_electronico.descripcion_estado = f"Error al solicitar inutilización: {error_desc}"
            doc_electronico.json_respuesta_api = response
            doc_electronico.save()
            raise Exception(f"Error de API al solicitar inutilización: {error_desc}")
    except DocumentoElectronico.DoesNotExist:
        print(f"DocumentoElectronico con ID {documento_electronico_id} no encontrado.")
        return {"status": "failed", "error": "Documento no encontrado"}
    except Exception as e:
        print(f"Excepción en solicitar_inutilizacion_task para DE {documento_electronico_id}: {e}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            doc = DocumentoElectronico.objects.filter(id=documento_electronico_id).first()
            if doc:
                doc.estado_sifen = 'error_api'
                doc.descripcion_estado = f"Fallo persistente al solicitar inutilización: {e}"
                doc.save()
            return {"status": "failed", "error": str(e)}
