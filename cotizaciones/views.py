from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import requests
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Cotizacion
from monedas.models import Moneda
from .forms import CotizacionForm
from django.db.models.functions import TruncDate
from django.db.models import Avg, F, OuterRef, Subquery, DecimalField, ExpressionWrapper
from django.utils.dateparse import parse_date
from django.utils import timezone
import datetime

from .models import CotizacionHistorica


@login_required
def cotizacion_list(request):
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
        return redirect("home") 

    cotizaciones = Cotizacion.objects.all()
    return render(request, 'cotizaciones/cotizacion_list.html', {'cotizaciones': cotizaciones})

# --- Crear cotización ---
@login_required
def cotizacion_create(request):
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
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
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
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
    if not request.user.has_perm("cotizaciones.access_cotizaciones"):
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

# --- API Serie temporal (pública: no requiere login) ---
def api_serie(request):
    base_code = (request.GET.get("base") or "PYG").upper()
    dest_code = (request.GET.get("destino") or "").upper()
    campo = (request.GET.get("campo") or "venta").lower()      # "venta" | "compra"
    agg = (request.GET.get("agg") or "last").lower()           # "last" | "avg"

    if not dest_code:
        return JsonResponse({"ok": False, "error": "Falta 'destino' (p.ej. USD)."}, status=400)
    if campo not in ("venta", "compra"):
        campo = "venta"
    if agg not in ("last", "avg"):
        agg = "last"

    today = timezone.localdate()
    default_desde = today - datetime.timedelta(days=90)
    desde = parse_date(request.GET.get("desde") or "") or default_desde
    hasta = parse_date(request.GET.get("hasta") or "") or today

    try:
        base = Moneda.objects.get(codigo=base_code)
        dest = Moneda.objects.get(codigo=dest_code)
    except Moneda.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Moneda no encontrada."}, status=404)

    qs = CotizacionHistorica.objects.filter(
        moneda_base=base, moneda_destino=dest,
        fecha__date__gte=desde, fecha__date__lte=hasta
    )

    # total_venta = valor_venta + comision_venta
    # total_compra = valor_compra - comision_compra
    if campo == "venta":
        expr = ExpressionWrapper(F("valor_venta") + F("comision_venta"),
                                 output_field=DecimalField(max_digits=12, decimal_places=4))
    else:
        expr = ExpressionWrapper(F("valor_compra") - F("comision_compra"),
                                 output_field=DecimalField(max_digits=12, decimal_places=4))

    if qs.exists():
        if agg == "avg":
            data_qs = (qs.annotate(dia=TruncDate("fecha"))
                         .values("dia")
                         .annotate(valor=Avg(expr))
                         .order_by("dia"))
            points = [{"x": r["dia"].isoformat(), "y": float(r["valor"])} for r in data_qs]
        else:  # "last" del día
            # Tomar el último registro de CADA día (DISTINCT ON)
            data_qs = (
                qs.annotate(dia=TruncDate("fecha"))
                .annotate(calc=expr)
                .order_by("dia", "-fecha")   # ordenar por día y dentro del día el más reciente
                .distinct("dia")             # nos quedamos con 1 por día
                .values("dia", "calc")
                .order_by("dia")
            )
            points = [{"x": r["dia"].isoformat(), "y": float(r["calc"])} for r in data_qs]

    else:
        # Fallback: si aún no hay histórico, devolvemos el valor actual
        try:
            cur = Cotizacion.objects.get(moneda_base=base, moneda_destino=dest)
            total = (cur.valor_venta + cur.comision_venta) if campo == "venta" else (cur.valor_compra - cur.comision_compra)
            points = [{"x": hasta.isoformat(), "y": float(total)}]
        except Cotizacion.DoesNotExist:
            points = []

    return JsonResponse({
        "ok": True,
        "pair": f"{base.codigo}/{dest.codigo}",
        "campo": campo,
        "agg": agg,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "points": points,
    })
