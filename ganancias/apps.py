from django.apps import AppConfig

class GananciasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ganancias'
    verbose_name = 'Módulo de Ganancias'

    def ready(self):
        import ganancias.signals  # Importar las señales aquí
