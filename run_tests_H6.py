"""
SOLUCIÓN NUCLEAR - Intercepta todos los prints
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

# Mock global
mock_stripe_gateway = MagicMock()
sys.modules["pagos.gateways.stripe_gateway"] = mock_stripe_gateway
mock_stripe_gateway.stripe = MagicMock()
mock_stripe_gateway.stripe.Charge.create.return_value = {"id": "test_charge"}
mock_stripe_gateway.stripe.PaymentIntent.create.return_value = {"id": "test_intent"}

# Configuración
warnings.filterwarnings("ignore", category=UserWarning, module="django")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CasaDeCambioIS2.settings")

# Deshabilitar TODO el logging
logging.disable(logging.CRITICAL)
os.environ['DJANGO_LOG_LEVEL'] = 'CRITICAL'

django.setup()

# -----------------------------
# INTERCEPTOR NUCLEAR - Redirige todos los prints
# -----------------------------
class OutputFilter:
    def __init__(self, original):
        self.original = original
        self.buffer = StringIO()
    
    def write(self, text):
        # Filtrar líneas con logs
        if any(pattern in text for pattern in ['INFO:', 'ERROR:', '[PAGOS]', '[WEBHOOK]']):
            self.buffer.write(text)  # Capturar pero no mostrar
        else:
            self.original.write(text)
    
    def flush(self):
        self.original.flush()

# -----------------------------
# Ejecutar tests con interceptor
# -----------------------------
out = StringIO()
try:
    with patch("pagos.gateways.stripe_gateway.stripe") as mock_stripe:
        mock_stripe.Charge.create.return_value = {"id": "test_charge"}
        mock_stripe.PaymentIntent.create.return_value = {"id": "test_intent"}
        
        apps_a_testear = ["roles", "notificaciones", "transacciones"]

        # Aplicar el filtro
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        output_filter = OutputFilter(original_stdout)
        
        sys.stdout = output_filter
        sys.stderr = output_filter
        
        try:
            call_command("test", *apps_a_testear, verbosity=1, stdout=out, stderr=out, interactive=False)
        finally:
            # Restaurar stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        result = out.getvalue()
        
        # Filtrar resultado final por si acaso
        filtered_lines = []
        for line in result.split('\n'):
            if not any(pattern in line for pattern in ['INFO:', 'ERROR:', '[PAGOS]', '[WEBHOOK]']):
                filtered_lines.append(line)
        
        filtered_result = '\n'.join(filtered_lines)
        
        # Mostrar resumen
        match = re.search(r"Ran (\d+) test", filtered_result)
        if match:
            print(f"Se ejecutaron {match.group(1)} pruebas.")

        if "\nOK\n" in filtered_result or "OK\n" in filtered_result:
            print("Pruebas unitarias exitosas")
        else:
            print(filtered_result)

except SystemExit:
    result = out.getvalue()
    filtered_lines = []
    for line in result.split('\n'):
        if not any(pattern in line for pattern in ['INFO:', 'ERROR:', '[PAGOS]', '[WEBHOOK]']):
            filtered_lines.append(line)
    print('\n'.join(filtered_lines))
except Exception as e:
    print(f"Error inesperado: {e}")