"""
RUN:SEED_H8 — Interceptor Nuclear para módulos Ganancias y Reportes
-------------------------------------------------------------------
Ejecuta las pruebas unitarias de los módulos ganancias y reportes
sin mostrar logs, prints ni warnings.
"""
import os
import sys
import django
from django.core.management import call_command
from io import StringIO
import warnings
import re
import logging

# -----------------------------
# CONFIGURACIÓN DJANGO
# -----------------------------
warnings.filterwarnings("ignore", category=UserWarning, module="django")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CasaDeCambioIS2.settings")

# Desactivar logs globales
logging.disable(logging.CRITICAL)
os.environ["DJANGO_LOG_LEVEL"] = "CRITICAL"

django.setup()

# -----------------------------
# INTERCEPTOR DE PRINTS Y LOGS
# -----------------------------
class OutputFilter:
    def __init__(self, original):
        self.original = original
        self.buffer = StringIO()

    def write(self, text):
        # Filtrar líneas con logs, warnings o etiquetas personalizadas
        if any(
            pattern in text
            for pattern in [
                "INFO:",
                "ERROR:",
                "WARNING",
                "DEBUG",
                "[GANANCIAS]",
                "[REPORTES]",
                "[API]",
                "[DOC]",
            ]
        ):
            self.buffer.write(text)  # Capturar sin mostrar
        else:
            self.original.write(text)

    def flush(self):
        self.original.flush()


# -----------------------------
# EJECUCIÓN DE TESTS GANANCIAS + REPORTES
# -----------------------------
out = StringIO()

try:
    apps_a_testear = ["ganancias", "reportes"]

    print("Ejecutando pruebas de los módulos Ganancias y Reportes...\n")

    # Aplicar filtro
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    output_filter = OutputFilter(original_stdout)

    sys.stdout = output_filter
    sys.stderr = output_filter

    try:
        call_command(
            "test",
            *apps_a_testear,
            verbosity=1,
            stdout=out,
            stderr=out,
            interactive=False,
        )
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    result = out.getvalue()

    # Filtrar resultado
    filtered_lines = [
        line
        for line in result.split("\n")
        if not any(
            p in line
            for p in [
                "INFO:",
                "ERROR:",
                "DEBUG",
                "[GANANCIAS]",
                "[REPORTES]",
                "[API]",
            ]
        )
    ]
    filtered_result = "\n".join(filtered_lines)

    # Mostrar resumen limpio
    match = re.search(r"Ran (\d+) test", filtered_result)
    if match:
        print(f"Se ejecutaron {match.group(1)} pruebas en total.")

    if "\nOK\n" in filtered_result or "OK\n" in filtered_result:
        print("Todas las pruebas unitarias de Ganancias y Reportes fueron exitosas.")
    else:
        print(filtered_result)

except SystemExit:
    result = out.getvalue()
    filtered_lines = [
        line
        for line in result.split("\n")
        if not any(p in line for p in ["INFO:", "ERROR:", "DEBUG", "[GANANCIAS]", "[REPORTES]", "[API]"])
    ]
    print("\n".join(filtered_lines))

except Exception as e:
    print(f" Error inesperado: {e}")
