# =========================
# apps.py
# =========================
from django.apps import AppConfig


class AnalistaPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analista_panel"
    verbose_name = "Panel del Analista"