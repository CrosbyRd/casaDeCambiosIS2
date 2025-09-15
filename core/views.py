# core/views.py
from django.shortcuts import render
from .forms import SimulacionForm
from .logic import calcular_simulacion

# Para Home/Rates dinámicos
from cotizaciones.models import Cotizacion


def pagina_inicio_y_simulador(request):
    form = SimulacionForm(request.POST or None)
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


# --- Home público con cotizaciones destacadas ---
def site_home(request):
    qs = (Cotizacion.objects
          .select_related('moneda_base', 'moneda_destino')
          .order_by('-fecha_actualizacion'))
    context = {
        # mostramos las 3 más recientes
        'cotizaciones_destacadas': list(qs[:3]),
    }
    return render(request, 'site/home.html', context)


# --- Rates público con todas las cotizaciones ---
def site_rates(request):
    qs = (Cotizacion.objects
          .select_related('moneda_base', 'moneda_destino')
          .order_by('moneda_destino__codigo'))
    context = {'cotizaciones': qs}
    return render(request, 'site/rates.html', context)
