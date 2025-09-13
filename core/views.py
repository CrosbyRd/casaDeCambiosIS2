# core/views.py
from django.shortcuts import render
from .forms import SimulacionForm
from .logic import calcular_simulacion

def pagina_inicio_y_simulador(request):
    form = SimulacionForm(request.POST or None) # Simplifica la instanciación
    resultado_simulacion = None

    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        
        resultado_simulacion = calcular_simulacion(
            monto_origen=datos['monto'],
            moneda_origen=datos['moneda_origen'],
            moneda_destino=datos['moneda_destino'],
            user=request.user
        )

    context = {
        'form': form,
        'resultado': resultado_simulacion
    }
    response = render(request, 'site/calculator.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
