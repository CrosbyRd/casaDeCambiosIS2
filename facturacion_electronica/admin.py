from django.contrib import admin
from .models import EmisorFacturaElectronica, DocumentoElectronico, ItemDocumentoElectronico

@admin.register(EmisorFacturaElectronica)
class EmisorFacturaElectronicaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruc', 'email_equipo', 'establecimiento', 'punto_expedicion', 'siguiente_numero_factura', 'rango_numeracion_inicio', 'rango_numeracion_fin', 'auth_token_present', 'token_generado_at')
    search_fields = ('nombre', 'ruc', 'email_equipo')
    list_filter = ('establecimiento', 'punto_expedicion')
    readonly_fields = ('token_generado_at',)
    fieldsets = (
        (None, {
            'fields': ('nombre', 'ruc', 'dv_ruc', 'email_emisor', 'direccion', 'numero_casa', 'telefono', 'actividades_economicas')
        }),
        ('Ubicación', {
            'fields': ('codigo_departamento', 'descripcion_departamento', 'codigo_ciudad', 'descripcion_ciudad')
        }),
        ('Configuración de Numeración', {
            'fields': ('establecimiento', 'punto_expedicion', 'email_equipo', 'rango_numeracion_inicio', 'rango_numeracion_fin', 'siguiente_numero_factura')
        }),
        ('API Factura Segura', {
            'fields': ('auth_token', 'token_generado_at')
        }),
    )

    def auth_token_present(self, obj):
        return bool(obj.auth_token)
    auth_token_present.boolean = True
    auth_token_present.short_description = "Token Presente"

class ItemDocumentoElectronicoInline(admin.TabularInline):
    model = ItemDocumentoElectronico
    extra = 1
    fields = ('codigo_interno', 'descripcion_producto_servicio', 'unidad_medida', 'cantidad', 'precio_unitario', 'descuento_item', 'afectacion_iva', 'proporcion_iva', 'tasa_iva')

@admin.register(DocumentoElectronico)
class DocumentoElectronicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'emisor', 'tipo_de', 'numero_documento_completo', 'cdc', 'estado_sifen', 'fecha_emision', 'transaccion_asociada')
    list_filter = ('tipo_de', 'estado_sifen', 'emisor__nombre')
    search_fields = ('cdc', 'numero_documento', 'emisor__ruc', 'transaccion_asociada__id')
    readonly_fields = ('id', 'cdc', 'fecha_emision', 'json_enviado_api', 'json_respuesta_api', 'url_kude', 'url_xml')
    inlines = [ItemDocumentoElectronicoInline]
    fieldsets = (
        (None, {
            'fields': ('emisor', 'tipo_de', 'numero_documento', 'numero_timbrado', 'cdc', 'estado_sifen', 'descripcion_estado', 'fecha_emision', 'transaccion_asociada')
        }),
        ('Detalles de la API', {
            'fields': ('json_enviado_api', 'json_respuesta_api', 'url_kude', 'url_xml'),
            'classes': ('collapse',)
        }),
    )

    def numero_documento_completo(self, obj):
        return f"{obj.emisor.establecimiento}-{obj.emisor.punto_expedicion}-{obj.numero_documento}"
    numero_documento_completo.short_description = "Número de Documento"
