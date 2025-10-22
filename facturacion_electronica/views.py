from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin # Mantener LoginRequiredMixin para las vistas basadas en clases
from django.contrib.auth.decorators import login_required # Importar los decoradores de permisos y login
from django.contrib import messages
from django.http import HttpResponse
from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico
from .forms import EmisorFacturaElectronicaForm
from .services import FacturaSeguraAPIClient
from .tasks import generar_factura_electronica_task, get_estado_sifen_task, solicitar_cancelacion_task, solicitar_inutilizacion_task
from .mixins import AdminRequiredMixin, admin_required # Importar el nuevo mixin y decorador
import json
import os

# Vistas para EmisorFacturaElectronica
class EmisorFacturaElectronicaListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = EmisorFacturaElectronica
    template_name = 'facturacion_electronica/emisor_list.html'
    context_object_name = 'emisores'

class EmisorFacturaElectronicaDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = EmisorFacturaElectronica
    template_name = 'facturacion_electronica/emisor_detail.html'
    context_object_name = 'emisor'

class EmisorFacturaElectronicaCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = EmisorFacturaElectronica
    form_class = EmisorFacturaElectronicaForm
    template_name = 'facturacion_electronica/emisor_form.html'
    success_url = reverse_lazy('facturacion_electronica:emisor_list')

    def form_valid(self, form):
        messages.success(self.request, "Emisor de Factura Electrónica creado exitosamente.")
        return super().form_valid(form)

class EmisorFacturaElectronicaUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = EmisorFacturaElectronica
    form_class = EmisorFacturaElectronicaForm
    template_name = 'facturacion_electronica/emisor_form.html'
    success_url = reverse_lazy('facturacion_electronica:emisor_list')

    def form_valid(self, form):
        messages.success(self.request, "Emisor de Factura Electrónica actualizado exitosamente.")
        return super().form_valid(form)

class EmisorFacturaElectronicaDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = EmisorFacturaElectronica
    template_name = 'facturacion_electronica/emisor_confirm_delete.html'
    success_url = reverse_lazy('facturacion_electronica:emisor_list')

    def form_valid(self, form):
        messages.success(self.request, "Emisor de Factura Electrónica eliminado exitosamente.")
        return super().form_valid(form)

# Vistas para DocumentoElectronico
class DocumentoElectronicoListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = DocumentoElectronico
    template_name = 'facturacion_electronica/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 20

class DocumentoElectronicoDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
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
@admin_required # Usar el decorador de función
def generar_token_view(request, emisor_id):
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
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if request.method == 'POST':
        try:
            get_estado_sifen_task.delay(str(documento.id))
            messages.info(request, "Solicitud de consulta de estado enviada. El estado se actualizará en breve.")
        except Exception as e:
            messages.error(request, f"Error al solicitar consulta de estado: {e}")
    return redirect('facturacion_electronica:documento_detail', pk=documento_id)

@login_required
@admin_required
def solicitar_cancelacion_de_view(request, documento_id):
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if request.method == 'POST':
        if documento.estado_sifen not in ['aprobado', 'aprobado_obs']:
            messages.error(request, "Solo se pueden cancelar documentos con estado 'Aprobado' o 'Aprobado con Observación'.")
            return redirect('facturacion_electronica:documento_detail', pk=documento_id)
        try:
            solicitar_cancelacion_task.delay(str(documento.id))
            messages.info(request, "Solicitud de cancelación enviada. El estado se actualizará en breve.")
        except Exception as e:
            messages.error(request, f"Error al solicitar cancelación: {e}")
    return redirect('facturacion_electronica:documento_detail', pk=documento_id)

@login_required
@admin_required
def solicitar_inutilizacion_de_view(request, documento_id):
    documento = get_object_or_404(DocumentoElectronico, id=documento_id)
    if request.method == 'POST':
        if documento.estado_sifen in ['aprobado', 'cancelado', 'inutilizado']:
            messages.error(request, "No se puede inutilizar un documento con estado 'Aprobado', 'Cancelado' o 'Inutilizado'.")
            return redirect('facturacion_electronica:documento_detail', pk=documento_id)
        try:
            solicitar_inutilizacion_task.delay(str(documento.id))
            messages.info(request, "Solicitud de inutilización enviada. El estado se actualizará en breve.")
        except Exception as e:
            messages.error(request, f"Error al solicitar inutilización: {e}")
    return redirect('facturacion_electronica:documento_detail', pk=documento_id)

@login_required
@admin_required
def descargar_kude_view(request, documento_id):
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
    emisor = get_object_or_404(EmisorFacturaElectronica, pk=pk)
    if request.method == 'POST':
        emisor.activo = not emisor.activo
        emisor.save()
        messages.success(request, f"El estado 'activo' del emisor {emisor.nombre} ha sido cambiado a {emisor.activo}.")
    return redirect('facturacion_electronica:emisor_detail', pk=pk)
