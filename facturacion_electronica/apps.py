from django.apps import AppConfig

class FacturacionElectronicaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facturacion_electronica'
    label = 'facturacion_electronica' # Añadir app_label explícito
