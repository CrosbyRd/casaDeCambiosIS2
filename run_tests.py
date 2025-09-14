import os
import sys
import django
from django.core.management import call_command
from io import StringIO
import warnings
import re

# -----------------------------
# Configuración inicial
# -----------------------------
# Ignorar warnings de Django
warnings.filterwarnings("ignore", category=UserWarning, module="django")

# Asegurarse de que Python encuentre tu proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Configurar settings de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CasaDeCambioIS2.settings") # Cambia si tu proyecto se llama distinto
django.setup()

# -----------------------------
# Ejecutar tests
# -----------------------------
out = StringIO()
try:
    call_command("test", "cotizaciones", verbosity=0, stdout=out, stderr=out)
    result = out.getvalue()

    # Detectar número de tests ejecutados
    match = re.search(r"Ran (\d+) test", result)
    if match:
        print(f"Se ejecutaron {match.group(1)} pruebas.")

    # Mostrar mensaje personalizado si todos pasaron
    if "\nOK\n" in result or "OK\n" in result:
        print("Pruebas unitarias exitosas")
    else:
        # Si hay errores o fallos, imprimir toda la salida
        print(result)

except SystemExit:
    # call_command termina con sys.exit() al final
    print(out.getvalue())
