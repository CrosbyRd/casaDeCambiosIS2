import subprocess
import sys

def run_seed(command):
    """Ejecuta un comando de seed y captura la salida."""
    print(f"\n=== Ejecutando {command} ===")
    result = subprocess.run(
        [sys.executable, "manage.py", command],
        capture_output=False,
        text=True
    )
    if result.returncode != 0:
        print(f"Error ejecutando {command}")
        sys.exit(1)
    print(f"=== {command} finalizado ===\n")


if __name__ == "__main__":
    # 1️⃣ Cargar clientes
    run_seed("seed_clientes")

    # 2️⃣ Cargar monedas
    run_seed("seed_monedas")

    # 3️⃣ Cargar cotizaciones (en guaraníes)
    run_seed("seed_tasas")

    # 4️⃣ Cargar tipos de pago
    run_seed("seed_pagos")

    # 5️⃣ Cargar campos dinámicos de medios de pago
    run_seed("seed_campos_pago")   # <--- Lo nuevo se agrega aquí

    # 6️⃣ Cargar medios de acreditación
    run_seed("seed_medio_acreditacion")
    # 7️⃣ Cargar campos dinámicos de medios de acreditación
    run_seed("seed_campos_acreditacion")   # 👈 NUEVO
    # 7️⃣ Cargar configuración general
    run_seed("seed_configuracion")
    # 8️⃣ Cargar terminales TED
    run_seed("seed_ted")

    print("✅ Todos los seeds ejecutados correctamente.")
