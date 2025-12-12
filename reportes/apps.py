"""
Configuración de la aplicación de reportes.

.. module:: reportes.apps
   :synopsis: Configuración de la app de reportes.

Esta app agrupa los reportes de ganancias y de transacciones
(pantallas web, exportes a PDF/Excel, etc.) integrados al
proyecto de casa de cambios.
"""

from django.apps import AppConfig


class ReportesConfig(AppConfig):

    """
    Configuración de la app ``reportes``.

    Define el nombre interno de la aplicación y el tipo de campo
    automático por defecto para los modelos.

    :cvar default_auto_field: Tipo de campo auto incremental por defecto.
    :cvar name: Nombre de la app dentro del proyecto Django.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reportes'
