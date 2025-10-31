"""
RUN:SEED_H7 — Interceptor Nuclear para facturacion_electronica
--------------------------------------------------------------
Ejecuta las pruebas unitarias del módulo facturacion_electronica
sin mostrar logs, prints, ni warnings.
"""

import os
import sys
import django
from django.core.management import call_command
from io import StringIO
import warnings
import re
import logging
from unittest.mock import MagicMock, patch

# -----------------------------
# MOCKS GLOBALES (si el módulo usa servicios externos)
# -----------------------------
mock_factura_segura = MagicMock()
sys.modules["facturacion_electronica.services.FacturaSeguraAPIClient"] = mock_factura_segura
mock_factura_segura.enviar_documento.return_value = {"estado": "ENVIADO"}

# -----------------------------
# CONFIGURACIÓN DJANGO
# -----------------------------
warnings.filterwarnings("ignore", category=UserWarning, module="django")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CasaDeCambioIS2.settings")

logging.disable(logging.CRITICAL)
os.environ['DJANGO_LOG_LEVEL'] = 'CRITICAL'

django.setup()

# -----------------------------
# INTERCEPTOR DE PRINTS Y LOGS
# -----------------------------
class OutputFilter:
    def __init__(self, original):
        self.original = original
        self.buffer = StringIO()
    
    def write(self, text):
        # Ignorar líneas de log, pero permitir salida importante
        if any(pattern in text for pattern in [
            'INFO:', 'ERROR:', 'WARNING', 'DEBUG', '[FACTURACION]', '[API]'
        ]):
            self.buffer.write(text)
        else:
            self.original.write(text)
    
    def flush(self):
        self.original.flush()

# -----------------------------
# EJECUCIÓN DE TESTS
# -----------------------------
out = StringIO()
try:
    # Mock controlado del cliente externo
    with patch("facturacion_electronica.services.requests") as mock_requests:
        mock_requests.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "OK"}
        )
        mock_requests.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"estado": "APROBADO"}
        )

        # Aplicar el filtro global de salida
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        output_filter = OutputFilter(original_stdout)
        
        sys.stdout = output_filter
        sys.stderr = output_filter

        try:
            call_command(
                "test",
                "facturacion_electronica",
                verbosity=1,
                stdout=out,
                stderr=out,
                interactive=False
            )
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        # Procesar resultado
        result = out.getvalue()
        filtered_lines = [
            line for line in result.split('\n')
            if not any(p in line for p in ['INFO:', 'ERROR:', 'DEBUG', '[FACTURACION]', '[API]'])
        ]
        filtered_result = '\n'.join(filtered_lines)

        # Mostrar resumen final
        match = re.search(r"Ran (\d+) test", filtered_result)
        if match:
            print(f"✅ Se ejecutaron {match.group(1)} pruebas.")

        if "\nOK\n" in filtered_result or "OK\n" in filtered_result:
            print("🎉 Todas las pruebas unitarias fueron exitosas.")
        

except SystemExit:
    result = out.getvalue()
    filtered_lines = [
        line for line in result.split('\n')
        if not any(p in line for p in ['INFO:', 'ERROR:', 'DEBUG', '[FACTURACION]', '[API]'])
    ]
    print('\n'.join(filtered_lines))
except Exception as e:
    print(f"💥 Error inesperado: {e}")
