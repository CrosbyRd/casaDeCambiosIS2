# CasaDeCambioIS2/views.py
from django.shortcuts import render    #devuelve una respuesta HTML
from cotizaciones.models import Cotizacion # Importar el modelo Cotizacion

def home(request):
    # Obtener las últimas cotizaciones para mostrar en la página de inicio
    cotizaciones_destacadas = Cotizacion.objects.all().select_related('moneda_base', 'moneda_destino').order_by('-fecha_actualizacion')[:5] # Obtener las 5 más recientes
    return render(request, 'site/home.html', {'cotizaciones_destacadas': cotizaciones_destacadas}) # Corregido: usar el nombre de variable correcto
