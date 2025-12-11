"""
Vistas de la aplicación **ganancias**.

.. module:: ganancias.views
   :synopsis: Dashboard analítico de ganancias para analistas y administradores.

Este módulo ofrece:

- :func:`is_analista_or_admin`: Helper de autorización para restringir el acceso
  a usuarios con rol de analista o staff.
- :func:`dashboard_ganancias`: Vista principal del reporte de ganancias, con
  filtros por rango de fechas, moneda operada y tipo de operación, además de
  métricas agregadas y datos preparados para gráficos.
"""


from django.shortcuts import render
from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import RegistroGanancia
from monedas.models import Moneda
from datetime import datetime, timedelta

# Mixin para proteger vistas por rol (ej. 'analista' o 'administrador')


def is_analista_or_admin(user):
    """
    Verifica si el usuario tiene permiso para ver el dashboard de ganancias.

    Se considera válido si:
    - Está autenticado, y
    - Tiene un rol M2M llamado "Analista" o "Administrador" (modelo Role del proyecto), o
    - Pertenece al grupo de Django "Analista", o
    - Es staff (is_staff=True).
    """
    if not user.is_authenticated:
        return False

    # 1) Proyecto actual: roles M2M (CustomUser.roles)
    roles_rel = getattr(user, "roles", None)
    if roles_rel is not None and roles_rel.filter(name__in=["Analista", "Administrador"]).exists():
        return True

    # 2) Compatibilidad con los tests: grupos clásicos de Django
    if user.groups.filter(name="Analista").exists():
        return True

    # 3) Staff también tiene acceso
    if user.is_staff:
        return True

    return False



@login_required
@user_passes_test(is_analista_or_admin)
def dashboard_ganancias(request):

    """
    Muestra el dashboard de reporte de ganancias.

    La vista permite filtrar los registros de :class:`ganancias.models.RegistroGanancia`
    y calcula métricas agregadas para mostrarlas en tablas y gráficos.

    Filtros disponibles (vía query string)
    --------------------------------------
    - ``fecha_inicio`` (YYYY-MM-DD): fecha mínima del registro de ganancia.
    - ``fecha_fin`` (YYYY-MM-DD): fecha máxima del registro de ganancia.
    - ``moneda_operada``: ID de la moneda extranjera operada.
    - ``tipo_operacion``: ``'compra'`` o ``'venta'`` según el tipo de transacción.

    Métricas calculadas
    -------------------
    - ``ganancia_total_periodo``: suma total de ``ganancia_registrada`` en el
      conjunto filtrado.
    - ``ganancias_por_dia``: queryset anotado con la ganancia total por día,
      usado para gráficos de tendencia.
    - ``ganancias_por_moneda``: lista de diccionarios con el total de
      ganancia por cada moneda operada.

    Contexto enviado a la plantilla
    -------------------------------
    - ``ganancia_total_periodo``: :class:`Decimal` o ``0`` si no hay registros.
    - ``ganancias_por_dia``: queryset con claves ``dia`` y ``total_dia``.
    - ``fechas_grafico``: lista de cadenas con fechas formateadas (YYYY-MM-DD).
    - ``totales_grafico``: lista de montos (``float``) por día.
    - ``ganancias_por_moneda``: lista serializable para gráficos (código, nombre, total).
    - ``todas_las_monedas``: queryset de :class:`monedas.models.Moneda` para el filtro.
    - ``fecha_inicio_seleccionada``, ``fecha_fin_seleccionada``,
      ``moneda_operada_seleccionada``, ``tipo_operacion_seleccionado``:
      valores actuales de los filtros para mantener el estado en el formulario.

    :param request: Objeto HTTP request.
    :type request: django.http.HttpRequest
    :return: Respuesta renderizada con la plantilla
             ``ganancias/dashboard_ganancias.html``.
    :rtype: django.http.HttpResponse
    """

    # --- Filtros ---
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    moneda_operada_id = request.GET.get('moneda_operada')
    tipo_operacion = request.GET.get('tipo_operacion')

    ganancias_queryset = RegistroGanancia.objects.all()

    if fecha_inicio_str:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        ganancias_queryset = ganancias_queryset.filter(fecha_registro__date__gte=fecha_inicio)
    else:
        # Si no se proporciona fecha_inicio_str, no aplicamos un filtro de fecha de inicio por defecto,
        # permitiendo que se muestren todos los registros históricos.
        fecha_inicio = None # No aplicar filtro de inicio por defecto
    if fecha_fin_str:
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        ganancias_queryset = ganancias_queryset.filter(fecha_registro__date__lte=fecha_fin)
    else:
        fecha_fin = None # No aplicar filtro de fin por defecto
        # Si no se proporciona fecha_fin_str, no aplicamos un filtro de fecha de fin por defecto,
        # permitiendo que se muestren todos los registros históricos.

    if moneda_operada_id:
        ganancias_queryset = ganancias_queryset.filter(moneda_operada__id=moneda_operada_id)

    if tipo_operacion in ['compra', 'venta']:
        ganancias_queryset = ganancias_queryset.filter(transaccion__tipo_operacion=tipo_operacion)

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
        'tipo_operacion_seleccionado': tipo_operacion,
    }
    return render(request, 'ganancias/dashboard_ganancias.html', context)
