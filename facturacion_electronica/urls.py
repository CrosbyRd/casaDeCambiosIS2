from django.urls import path
from . import views

app_name = 'facturacion_electronica'

urlpatterns = [
    # URLs para EmisorFacturaElectronica
    path('emisores/', views.EmisorFacturaElectronicaListView.as_view(), name='emisor_list'),
    path('emisores/crear/', views.EmisorFacturaElectronicaCreateView.as_view(), name='emisor_create'),
    path('emisores/<int:pk>/', views.EmisorFacturaElectronicaDetailView.as_view(), name='emisor_detail'),
    path('emisores/<int:pk>/editar/', views.FacturacionElectronicaPermissionMixin.as_view(template_name='facturacion_electronica/emisor_form.html', model=views.EmisorFacturaElectronica, form_class=views.EmisorFacturaElectronicaForm), name='emisor_update'),
    path('emisores/<int:pk>/eliminar/', views.EmisorFacturaElectronicaDeleteView.as_view(), name='emisor_delete'),
    path('emisores/<int:emisor_id>/generar_token/', views.generar_token_view, name='generar_token'),

    # URLs para DocumentoElectronico
    path('documentos/', views.DocumentoElectronicoListView.as_view(), name='documento_list'),
    path('documentos/<uuid:pk>/', views.DocumentoElectronicoDetailView.as_view(), name='documento_detail'),
    path('documentos/<uuid:documento_id>/consultar_estado/', views.consultar_estado_de_view, name='consultar_estado'),
    path('documentos/<uuid:documento_id>/cancelar/', views.solicitar_cancelacion_de_view, name='solicitar_cancelacion'),
    path('documentos/<uuid:documento_id>/inutilizar/', views.solicitar_inutilizacion_de_view, name='solicitar_inutilizacion'),
    path('documentos/<uuid:documento_id>/descargar_kude/', views.descargar_kude_view, name='descargar_kude'),
    path('documentos/<uuid:documento_id>/descargar_xml/', views.descargar_xml_view, name='descargar_xml'),
]
