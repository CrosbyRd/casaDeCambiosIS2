#!/bin/bash
# Este script soluciona un problema de inconsistencia en las migraciones de Django
# para las aplicaciones 'pagos' y 'simuladores'.
# 1. "chmod +x fix_migrations.sh" <--- desde la raiz del proyecto meter este comando sin las comillas
# 2. "./fix_migrations.sh" <--- desde la raiz del proyecto meter este comando sin las comillas
# Poner en pausa el script si cualquier comando falla
set -e

echo "Paso 1: Revertiendo el historial de migraciones de 'pagos' y 'simuladores' (modo --fake)..."
python manage.py migrate pagos zero --fake
python manage.py migrate simuladores zero --fake
echo "Historial de migraciones revertido."
echo "-----------------------------------"

echo "Paso 2: Eliminando archivos de migración antiguos..."
find pagos/migrations/ -type f -name "*.py" -not -name "__init__.py" -delete
find simuladores/migrations/ -type f -name "*.py" -not -name "__init__.py" -delete
echo "Archivos de migración eliminados."
echo "-----------------------------------"

echo "Paso 3: Creando nuevas migraciones iniciales..."
python manage.py makemigrations pagos simuladores
echo "Nuevas migraciones creadas."
echo "-----------------------------------"

echo "Paso 4: Aplicando las nuevas migraciones a la base de datos..."
python manage.py migrate
echo "Migraciones aplicadas correctamente."
echo "-----------------------------------"

echo "¡Proceso completado! La base de datos ha sido sincronizada."
