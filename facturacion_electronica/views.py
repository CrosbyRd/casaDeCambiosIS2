"""
Vistas de la app Facturación Electrónica.

.. module:: facturacion_electronica.views
   :synopsis: Vistas propias del módulo de Facturación Electrónica.

Este módulo contiene las vistas para la gestión de emisores y documentos electrónicos,
incluyendo operaciones CRUD y acciones relacionadas con la API de Factura Segura y SIFEN.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin  # Mantener LoginRequiredMixin para las vistas basadas en clases
from django.contrib.auth.decorators import login_required  # Importar los decoradores de permisos y login
from django.contrib import messages
from django.http import HttpResponse
from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico
from .forms import EmisorFacturaElectronicaForm
from .services import FacturaSeguraAPIClient
from .tasks import (
    generar_factura_electronica_task,
    get_estado_sifen_task,
    solicitar_cancelacion_task,
    solicitar_inutilizacion_task,
)
from .mixins import AdminRequiredMixin, admin_required  # Importar el nuevo mixin y decorador
import json
from django.db import transaction
import os


# Vistas para EmisorFacturaElectronica
class EmisorFacturaElectronicaListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Vista para listar todos los emisores de factura electrónica.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Muestra una lista paginada de emisores.
    """
    model = EmisorFacturaElectronica
    template_name = 'facturacion_electronica/emisor_list.html'
    context_object_name = 'emisores'


class EmisorFacturaElectronicaDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """
    Vista para mostrar los detalles de un emisor de factura electrónica específico.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    """
    model = EmisorFacturaElectronica
    template_name = 'facturacion_electronica/emisor_detail.html'
    context_object_name = 'emisor'


class EmisorFacturaElectronicaCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    Vista para crear un nuevo emisor de factura electrónica.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Almacena los datos del formulario y muestra un mensaje de éxito.
    """
    model = EmisorFacturaElectronica
    form_class = EmisorFacturaElectronicaForm
    template_name = 'facturacion_electronica/emisor_form.html'
    success_url = reverse_lazy('facturacion_electronica:emisor_list')

    def form_valid(self, form):
        messages.success(self.request, "Emisor de Factura Electrónica creado exitosamente.")
        return super().form_valid(form)


class EmisorFacturaElectronicaUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    Vista para actualizar un emisor de factura electrónica existente.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Actualiza los datos del formulario y muestra un mensaje de éxito.
    """
    model = EmisorFacturaElectronica
    form_class = EmisorFacturaElectronicaForm
    template_name = 'facturacion_electronica/emisor_form.html'
    success_url = reverse_lazy('facturacion_electronica:emisor_list')

    def form_valid(self, form):
        messages.success(self.request, "Emisor de Factura Electrónica actualizado exitosamente.")
        return super().form_valid(form)


class EmisorFacturaElectronicaDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Vista para eliminar un emisor de factura electrónica.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Elimina el emisor y todos los documentos electrónicos relacionados de forma atómica.
    """
    model = EmisorFacturaElectronica
    template_name = "facturacion_electronica/emisor_confirm_delete.html"
    context_object_name = "object"
    success_url = reverse_lazy("facturacion_electronica:emisor_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        with transaction.atomic():
            # Borrar primero TODOS los documentos vinculados (usar related_name correcto)
            relacionados = self.object.documentos_electronicos.all()
            eliminados = relacionados.count()
            for doc in relacionados:
                # Si el modelo tiene FileFields (PDF/KuDE), esto asegura que se borren del storage:
                doc.delete()
            # Luego borrar el emisor
            self.object.delete()

        messages.success(
            request,
            f"Emisor eliminado correctamente. También se eliminaron {eliminados} documento(s) electrónico(s) relacionado(s)."
        )
        return redirect(success_url)


# Vistas para DocumentoElectronico
class DocumentoElectronicoListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Vista para listar todos los documentos electrónicos.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Muestra una lista paginada de documentos electrónicos.
    """
    model = DocumentoElectronico
    template_name = 'facturacion_electronica/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 20


class DocumentoElectronicoDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """
    Vista para mostrar los detalles de un documento electrónico específico.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Prepara los JSON de envío y respuesta de la API para una visualización legible.
    """
    model = DocumentoElectronico
    template_name = 'facturacion_electronica/documento_detail.html'
    context_object_name = 'documento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['json_enviado_pretty'] = json.dumps(self.object.json_enviado_api, indent=2) if self.object.json_enviado_api else None
        context['json_respuesta_pretty'] = json.dumps(self.object.json_respuesta_api, indent=2) if self.object.json_respuesta_api else None
        return context


# Acciones para DocumentoElectronico (disparadas por POST)
@login_required
@admin_required  # Usar el decorador de función
def generar_token_view(request, emisor_id):
    """
    Vista para generar o actualizar el token de autenticación de un emisor.

    Requiere una solicitud POST. Dispara la generación del token a través del cliente de la API.

    :param request: Objeto HttpRequest.
    :param emisor_id: ID del emisor.
    :type emisor_id: int
    :return: Redirecciona a la vista de detalle del emisor con un mensaje.
    :rtype: HttpResponseRedirect
    """
    emisor = get_object_or_404(EmisorFacturaElectronica, id=emisor_id)
    if request.method == 'POST':
        try:
            client = FacturaSeguraAPIClient(emisor.id)
            client._generate_auth_token()
            messages.success(request, "Token de autenticación generado/actualizado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al generar token: {e}")
    return redirect('facturacion_electronica:emisor_detail', pk=emisor_id)


@login_required
@admin_required
def consultar_estado_de_view(request, documento_id):
    """
    Vista para consultar el estado de un documento electrónico en SIFEN.

    Requiere una solicitud POST. Dispara una tarea asíncrona para consultar el estado.

    :param request: Objeto HttpRequest.
    :param documento_id: ID del documento electrónico.
    :type documento_id: uuid.UUID
    :return: Redirecciona a la vista de detalle del documento con un mensaje.
    :rtype: HttpResponseRedirect
    """
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if request.method == 'POST':
        try:
            # pasar UUID directamente
            get_estado_sifen_task.delay(documento.id)
            messages.info(request, "Solicitud de consulta de estado enviada. El estado se actualizará en breve.")
        except Exception as e:
            messages.error(request, f"Error al solicitar consulta de estado: {e}")
    return redirect('facturacion_electronica:documento_detail', pk=documento_id)


@login_required
@admin_required
def solicitar_cancelacion_de_view(request, documento_id):
    """
    Vista para solicitar la cancelación de un documento electrónico en SIFEN.

    Requiere una solicitud POST. Solo permite cancelar documentos en estado 'Aprobado' o 'Aprobado con Observación'.
    Dispara una tarea asíncrona para solicitar la cancelación.

    :param request: Objeto HttpRequest.
    :param documento_id: ID del documento electrónico.
    :type documento_id: uuid.UUID
    :return: Redirecciona a la vista de detalle del documento con un mensaje.
    :rtype: HttpResponseRedirect
    """
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if request.method == 'POST':
        if documento.estado_sifen not in ['aprobado', 'aprobado_obs']:
            messages.error(request, "Solo se pueden cancelar documentos con estado 'Aprobado' o 'Aprobado con Observación'.")
            return redirect('facturacion_electronica:documento_detail', pk=documento_id)
        try:
            solicitar_cancelacion_task.delay(documento.id)
            messages.info(request, "Solicitud de cancelación enviada. El estado se actualizará en breve.")
        except Exception as e:
            messages.error(request, f"Error al solicitar cancelación: {e}")
    return redirect('facturacion_electronica:documento_detail', pk=documento_id)


@login_required
@admin_required
def solicitar_inutilizacion_de_view(request, documento_id):
    """
    Vista para solicitar la inutilización de un documento electrónico en SIFEN.

    Requiere una solicitud POST. No permite inutilizar documentos ya 'Aprobados', 'Cancelados' o 'Inutilizados'.
    Dispara una tarea asíncrona para solicitar la inutilización.

    :param request: Objeto HttpRequest.
    :param documento_id: ID del documento electrónico.
    :type documento_id: uuid.UUID
    :return: Redirecciona a la vista de detalle del documento con un mensaje.
    :rtype: HttpResponseRedirect
    """
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if request.method == 'POST':
        if documento.estado_sifen in ['aprobado', 'cancelado', 'inutilizado']:
            messages.error(request, "No se puede inutilizar un documento con estado 'Aprobado', 'Cancelado' o 'Inutilizado'.")
            return redirect('facturacion_electronica:documento_detail', pk=documento_id)
        try:
            solicitar_inutilizacion_task.delay(documento.id)
            messages.info(request, "Solicitud de inutilización enviada. El estado se actualizará en breve.")
        except Exception as e:
            messages.error(request, f"Error al solicitar inutilización: {e}")
    return redirect('facturacion_electronica:documento_detail', pk=documento_id)


@login_required
@admin_required
def descargar_kude_view(request, documento_id):
    """
    Vista para descargar el KuDE (Representación Gráfica del Documento Electrónico).

    Requiere que el documento tenga un CDC asignado. Utiliza el cliente de la API
    para obtener el contenido PDF del KuDE.

    :param request: Objeto HttpRequest.
    :param documento_id: ID del documento electrónico.
    :type documento_id: uuid.UUID
    :return: Un HttpResponse con el contenido PDF o una redirección con mensaje de error.
    :rtype: HttpResponse or HttpResponseRedirect
    """
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if not documento.cdc:
        messages.error(request, "El documento no tiene un CDC asignado para descargar el KuDE.")
        return redirect('facturacion_electronica:documento_detail', pk=documento_id)

    try:
        client = FacturaSeguraAPIClient(documento.emisor.id)
        pdf_content = client.descargar_kude(documento.cdc, documento.emisor.ruc)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="kude_{documento.cdc}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error al descargar KuDE: {e}")
        return redirect('facturacion_electronica:documento_detail', pk=documento_id)


@login_required
@admin_required
def descargar_xml_view(request, documento_id):
    """
    Vista para descargar el archivo XML de un documento electrónico.

    Requiere que el documento tenga un CDC asignado. Utiliza el cliente de la API
    para obtener el contenido XML del documento.

    :param request: Objeto HttpRequest.
    :param documento_id: ID del documento electrónico.
    :type documento_id: uuid.UUID
    :return: Un HttpResponse con el contenido XML o una redirección con mensaje de error.
    :rtype: HttpResponse or HttpResponseRedirect
    """
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if not documento.cdc:
        messages.error(request, "El documento no tiene un CDC asignado para descargar el XML.")
        return redirect('facturacion_electronica:documento_detail', pk=documento_id)

    try:
        client = FacturaSeguraAPIClient(documento.emisor.id)
        xml_content = client.descargar_xml(documento.cdc, documento.emisor.ruc)
        response = HttpResponse(xml_content, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="de_{documento.cdc}.xml"'
        return response
    except Exception as e:
        messages.error(request, f"Error al descargar XML: {e}")
        return redirect('facturacion_electronica:documento_detail', pk=documento_id)


@login_required
@admin_required
def toggle_emisor_activo_view(request, pk):
    """
    Vista para cambiar el estado 'activo' de un emisor de factura electrónica.

    Requiere una solicitud POST. Alterna el valor del campo `activo` del emisor.

    :param request: Objeto HttpRequest.
    :param pk: Clave primaria del emisor.
    :type pk: int
    :return: Redirecciona a la vista de detalle del emisor con un mensaje.
    :rtype: HttpResponseRedirect
    """
    emisor = get_object_or_404(EmisorFacturaElectronica, pk=pk)
    if request.method == 'POST':
        emisor.activo = not emisor.activo
        emisor.save()
        messages.success(request, f"El estado 'activo' del emisor {emisor.nombre} ha sido cambiado a {emisor.activo}.")
    return redirect('facturacion_electronica:emisor_detail', pk=pk)


@login_required
@admin_required
def consultar_estado(request, pk):
    """
    Dispara la consulta de estado de un documento electrónico en SIFEN.

    Esta función es asíncrona (usa Celery) y no bloquea la UI. Proporciona
    feedback inmediato al usuario mientras la consulta se procesa en segundo plano.

    :param request: Objeto HttpRequest.
    :param pk: Clave primaria del documento electrónico.
    :type pk: uuid.UUID
    :return: Redirecciona a la vista de detalle del documento con un mensaje informativo.
    :rtype: HttpResponseRedirect
    """
    doc = get_object_or_404(DocumentoElectronico, pk=pk)

    # dispara la consulta asíncrona
    get_estado_sifen_task.delay(doc.id)

    # feedback inmediato al usuario (mostrado en documento_detail.html)
    messages.info(
        request,
        f"Consulta enviada a SIFEN. Estado actual: {doc.get_estado_sifen_display()}."
    )

    # redirige al detalle para que vea el badge/estado
    return redirect("facturacion_electronica:documento_detail", pk=pk)


class DocumentoElectronicoDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Vista para eliminar un documento electrónico.

    Requiere que el usuario esté autenticado y tenga permisos de administrador.
    Elimina el documento y muestra un mensaje de éxito.
    """
    model = DocumentoElectronico
    template_name = "facturacion_electronica/documento_confirm_delete.html" # Podríamos crear una plantilla específica si se necesita confirmación
    context_object_name = "documento"
    success_url = reverse_lazy("facturacion_electronica:documento_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(request, f"Documento electrónico {self.object} eliminado correctamente.")
        return redirect(success_url)
