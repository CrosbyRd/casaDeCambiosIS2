# core/views.py
from django.shortcuts import render
from .forms import SimulacionForm
from .logic import calcular_simulacion

def pagina_inicio_y_simulador(request):
    form = SimulacionForm(request.POST or None) # Simplifica la instanciación
    resultado_simulacion = None

    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        
        # Lógica de segmentación simulada
        tipo_cliente = 'MINORISTA'
        if request.user.is_authenticated:
            # En el futuro, aquí obtendríamos el segmento del cliente real.
            # Por ahora, simulamos que un usuario logueado es VIP para ver la diferencia.
            tipo_cliente = 'VIP'

        resultado_simulacion = calcular_simulacion(
            monto_origen=datos['monto'],
            moneda_origen=datos['moneda_origen'],
            moneda_destino=datos['moneda_destino'],
            tipo_cliente=tipo_cliente
        )

    context = {
        'form': form,
        'resultado': resultado_simulacion
    }
    # return render(request, 'core/inicio.html', context)
    return render(request, 'site/calculator.html', context)