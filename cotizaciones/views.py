from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import requests
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Cotizacion
from monedas.models import Moneda
from .forms import CotizacionForm
# --- Función auxiliar para verificar si es admin ---
def es_admin(user):
    return user.is_authenticated and user.is_staff

# --- Lista de cotizaciones ---
@login_required
def cotizacion_list(request):
    cotizaciones = Cotizacion.objects.all()
    return render(request, 'cotizaciones/cotizacion_list.html', {'cotizaciones': cotizaciones})

# --- Crear cotización ---
@login_required
def cotizacion_create(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")
    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        if form.is_valid():
            try:
                moneda_base = Moneda.objects.get(codigo='PYG')
                if Cotizacion.objects.filter(
                    moneda_base=moneda_base,
                    moneda_destino=form.cleaned_data['moneda_destino']
                ).exists():
                    messages.error(request, "Ya existe una cotización para esta moneda destino.")
                else:
                    form.instance.moneda_base = moneda_base
                    form.save()
                    messages.success(request, "Cotización guardada correctamente.")
                    return redirect('cotizaciones:cotizacion_list')
            except Moneda.DoesNotExist:
                messages.error(request, "La moneda base Guaraní (PYG) no está registrada.")
    else:
        form = CotizacionForm()

    return render(request, 'cotizaciones/cotizacion_form.html', {'form': form})

# --- Actualizar cotización ---
@login_required
def cotizacion_update(request, pk):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")
    
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        form = CotizacionForm(request.POST, instance=cotizacion)
        if form.is_valid():
            form.save()
            messages.success(request, "Cotización actualizada correctamente.")
            return redirect('cotizaciones:cotizacion_list')
    else:
        form = CotizacionForm(instance=cotizacion)

    return render(request, 'cotizaciones/cotizacion_form.html', {'form': form})

# --- Eliminar cotización ---
@login_required
def cotizacion_delete(request, pk):

    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")
    
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        cotizacion.delete()
        messages.success(request, "Cotización eliminada correctamente.")
        return redirect('cotizaciones:cotizacion_list')
    
    return render(request, 'cotizaciones/cotizacion_confirm_delete.html', {'cotizacion': cotizacion})

# --- Vista para obtener valores desde API ---
@login_required
def obtener_valores_api(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")
    
    moneda_destino_id = request.GET.get('moneda_destino_id')
    if not moneda_destino_id:
        return JsonResponse({'success': False, 'error': 'Falta el parámetro moneda_destino_id'}, status=400)
    
    try:
        moneda_destino = Moneda.objects.get(id=moneda_destino_id)
        valores = obtener_cotizacion_api(moneda_destino.codigo)
        
        if valores:
            return JsonResponse({
                'success': True,
                'valor_compra': valores['valor_compra'],
                'valor_venta': valores['valor_venta'],
                'moneda': moneda_destino.codigo,
                'fuente': 'API en tiempo real'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f"No se pudieron obtener valores para {moneda_destino.codigo} desde la API. Ingrese los valores manualmente."
            }, status=404)
            
    except Moneda.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Moneda no encontrada'}, status=404)

# --- Función para consultar API HexaRate ---
def obtener_cotizacion_api(moneda_destino_codigo):

    
    """
    Obtiene valor de compra y venta desde currency-api (sin necesidad de clave)
    Devuelve un diccionario: {'valor_compra': float, 'valor_venta': float} o None si falla.
    """
    api_url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/pyg/{moneda_destino_codigo.lower()}.json"
    
    try:
        response = requests.get(api_url, timeout=10)
        data = response.json()
        
        tasa = data.get(moneda_destino_codigo.lower())
        if tasa:
            return {'valor_compra': float(tasa), 'valor_venta': float(tasa)}
        
        return None
    except Exception as e:
        print(f"Error con API {api_url}: {e}")
        return None
