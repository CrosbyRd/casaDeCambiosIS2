# notificaciones/apps.py
from django.apps import AppConfig

class NotificacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificaciones'

    def ready(self):
        # Importar las señales para que se registren
        import notificaciones.signals
