# cotizaciones/apps.py
from django.apps import AppConfig

class CotizacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cotizaciones"

    def ready(self):
        from . import signals  # noqa: F401
