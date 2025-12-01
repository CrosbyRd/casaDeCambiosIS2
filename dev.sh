#!/bin/bash

# Este script ejecuta los tres comandos necesarios para levantar el proyecto en modo desarrollo,
# cada uno en una terminal separada.

# Navegar al directorio del proyecto Django de forma relativa
cd casaDeCambiosIS2

echo "Iniciando servidor Django..."
x-terminal-emulator -e "bash -c 'python manage.py runserver; exec bash'" &

echo "Iniciando Celery Worker..."
x-terminal-emulator -e "bash -c 'celery -A CasaDeCambioIS2 worker -l info; exec bash'" &

echo "Iniciando Stripe Listener..."
x-terminal-emulator -e "bash -c 'stripe listen --forward-to localhost:8000/payments/webhook/; exec bash'" &

echo "Todos los servicios han sido iniciados en terminales separadas. La ventana actual puede cerrarse."
