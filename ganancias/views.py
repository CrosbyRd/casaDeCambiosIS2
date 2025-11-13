from django.shortcuts import render
from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import RegistroGanancia
from monedas.models import Moneda
from datetime import datetime, timedelta

# Mixin para proteger vistas por rol (ej. 'analista' o 'administrador')
def is_analista_or_admin(user):
    return user.is_authenticated and (user.groups.filter(name='Analista').exists() or user.is_staff)

@login_required
@user_passes_test(is_analista_or_admin)
def dashboard_ganancias(request):
    # --- Filtros ---
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    moneda_operada_id = request.GET.get('moneda_operada')

    ganancias_queryset = RegistroGanancia.objects.all()

    if fecha_inicio_str:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        ganancias_queryset = ganancias_queryset.filter(fecha_registro__date__gte=fecha_inicio)
    else:
        fecha_inicio = (datetime.now() - timedelta(days=30)).date() # Por defecto, últimos 30 días
        ganancias_queryset = ganancias_queryset.filter(fecha_registro__date__gte=fecha_inicio)

    if fecha_fin_str:
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        ganancias_queryset = ganancias_queryset.filter(fecha_registro__date__lte=fecha_fin)
    else:
        fecha_fin = datetime.now().date() # Por defecto, hasta hoy
        ganancias_queryset = ganancias_queryset.filter(fecha_registro__date__lte=fecha_fin)

    if moneda_operada_id:
        ganancias_queryset = ganancias_queryset.filter(moneda_operada__id=moneda_operada_id)

    # --- Métricas Clave ---
    ganancia_total_periodo = ganancias_queryset.aggregate(total=Sum('ganancia_registrada'))['total'] or 0

    # Ganancias por día para el gráfico de tendencias
    ganancias_por_dia = ganancias_queryset.annotate(
        dia=TruncDate('fecha_registro')
    ).values('dia').annotate(
        total_dia=Sum('ganancia_registrada')
    ).order_by('dia')

    fechas_grafico = [g['dia'].strftime('%Y-%m-%d') for g in ganancias_por_dia]
    totales_grafico = [float(g['total_dia']) for g in ganancias_por_dia]

    # Ganancias por moneda operada
    ganancias_por_moneda_queryset = ganancias_queryset.values(
        'moneda_operada__codigo', 'moneda_operada__nombre'
    ).annotate(
        total_moneda=Sum('ganancia_registrada')
    ).order_by('-total_moneda')

    # Convertir el QuerySet a una lista de diccionarios para serialización JSON
    ganancias_por_moneda_lista = list(ganancias_por_moneda_queryset)

    # Obtener todas las monedas para el filtro
    todas_las_monedas = Moneda.objects.all().order_by('codigo')

    context = {
        'ganancia_total_periodo': ganancia_total_periodo,
        'ganancias_por_dia': ganancias_por_dia,
        'fechas_grafico': fechas_grafico,
        'totales_grafico': totales_grafico,
        'ganancias_por_moneda': ganancias_por_moneda_lista, # Usar la lista serializable
        'todas_las_monedas': todas_las_monedas,
        'fecha_inicio_seleccionada': fecha_inicio_str,
        'fecha_fin_seleccionada': fecha_fin_str,
        'moneda_operada_seleccionada': moneda_operada_id,
    }
    return render(request, 'ganancias/dashboard_ganancias.html', context)
