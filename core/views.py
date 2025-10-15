from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.urls import reverse
from django.utils.timezone import now
from .forms import SimulacionForm, OperacionForm
from .logic import calcular_simulacion
from monedas.models import Moneda
from cotizaciones.models import Cotizacion
from clientes.models import Cliente
from configuracion.models import TransactionLimit
from transacciones.models import Transaccion
import uuid
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date
from core.utils import validar_limite_transaccion
from usuarios.utils import get_cliente_activo
from pagos.models import TipoMedioPago
from pagos.services import iniciar_cobro_a_cliente

def calculadora_view(request):
    form = SimulacionForm(request.POST or None)
    resultado = None

    if request.method == 'POST' and form.is_valid():
        monto_origen = form.cleaned_data['monto']
        moneda_origen = form.cleaned_data['moneda_origen']
        moneda_destino = form.cleaned_data['moneda_destino']

        # Si el usuario hace clic en "Proceder a Operación", redirigir a la vista de inicio de operación.
        if 'proceder' in request.POST:
            import urllib.parse
            query_params = {
                'monto': monto_origen,
                'moneda_origen': moneda_origen,
                'moneda_destino': moneda_destino,
            }
            # Construir la URL con parámetros GET para pre-rellenar el formulario en la siguiente vista.
            redirect_url = f"{reverse('core:iniciar_operacion')}?{urllib.parse.urlencode(query_params)}"
            return redirect(redirect_url)

        # Si es solo un cálculo, procesar y mostrar el resultado en la misma página.
        resultado = calcular_simulacion(monto_origen, moneda_origen, moneda_destino, user=request.user)

        if resultado and resultado.get('error'):
            messages.error(request, resultado['error'])
            resultado = None

    iniciar_operacion_url = request.build_absolute_uri(reverse('core:iniciar_operacion'))
    return render(request, 'site/calculator.html', {'form': form, 'resultado': resultado, 'iniciar_operacion_url': iniciar_operacion_url})


def site_rates(request):
    cotizaciones = Cotizacion.objects.all().select_related('moneda_base', 'moneda_destino')
    return render(request, 'site/rates.html', {'cotizaciones': cotizaciones})



@login_required
def iniciar_operacion(request):
    # Asegurarse de que haya un cliente activo
    cliente = get_cliente_activo(request)  # Usamos get_cliente_activo para obtener el cliente activo
    if not cliente:
        messages.info(request, "Seleccioná con qué cliente querés operar.")
        return redirect("usuarios:seleccionar_cliente")  # Redirige a la página de selección de cliente

    initial_data = {}

    # Obtener los parámetros de la URL si están presentes
    if request.method == 'GET':
        monto_from_url = request.GET.get('monto')
        moneda_origen_from_url = request.GET.get('moneda_origen')
        moneda_destino_from_url = request.GET.get('moneda_destino')

        if monto_from_url and moneda_origen_from_url and moneda_destino_from_url:
            initial_data = {
                'monto': monto_from_url,
                'moneda_origen': moneda_origen_from_url,
                'moneda_destino': moneda_destino_from_url,
                'tipo_operacion': 'venta' if moneda_origen_from_url == 'PYG' else 'compra'
            }

    form = OperacionForm(request.POST or initial_data)
    resultado_simulacion = None

    # Calcular el límite disponible para el cliente
    limite_cfg = TransactionLimit.objects.filter(moneda__codigo='PYG').first()  # Límite en PYG
    limite_disponible = Decimal(limite_cfg.monto_diario) if limite_cfg else Decimal(0)

    # Obtener las transacciones del día y calcular el total consumido por el cliente
    hoy = now().date()

    total_transacciones_hoy = Transaccion.objects.filter(
        cliente=cliente,  # <--- ¡REVERTIDO a la variable cliente!
        fecha_creacion__date=hoy
    ).aggregate(Sum('monto_origen'))['monto_origen__sum'] or Decimal(0)

    limite_disponible -= total_transacciones_hoy  # Límite disponible = Límite diario - Total transacciones hoy

    # Procesar el formulario
    if request.method == 'POST' and form.is_valid():
        tipo_operacion = form.cleaned_data['tipo_operacion']
        monto_origen = form.cleaned_data['monto']
        moneda_origen_codigo = form.cleaned_data['moneda_origen']
        moneda_destino_codigo = form.cleaned_data['moneda_destino']

        # Verificación de la simulación y la validación de los límites
        resultado_simulacion = calcular_simulacion(monto_origen, moneda_origen_codigo, moneda_destino_codigo, user=request.user)

        if resultado_simulacion.get('error'):
            messages.error(request, resultado_simulacion['error'])
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        # Validar el límite disponible
        if monto_origen > limite_disponible:
            messages.error(request, f"El monto excede el límite disponible de {limite_disponible} PYG.")
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        # Proceder con la operación
        operacion_data = {
            'tipo_operacion': tipo_operacion,
            'moneda_origen_codigo': moneda_origen_codigo,
            'monto_origen': str(monto_origen),
            'moneda_destino_codigo': moneda_destino_codigo,
            'monto_recibido': str(resultado_simulacion['monto_recibido']),
            'tasa_aplicada': str(resultado_simulacion['tasa_aplicada']),
            'comision_aplicada': str(resultado_simulacion['bonificacion_aplicada']),
            'modalidad_tasa': form.cleaned_data['modalidad_tasa'], # Añadir modalidad de tasa
        }
        # Añadir medio de pago si fue seleccionado
        if form.cleaned_data.get('medio_pago'):
            operacion_data['medio_pago_id'] = str(form.cleaned_data['medio_pago'].id_tipo)

        request.session['operacion_pendiente'] = operacion_data

        return redirect('core:confirmar_operacion')

    # Pasar el límite disponible al template
    return render(request, 'core/iniciar_operacion.html', {
        'form': form,
        'resultado_simulacion': resultado_simulacion,
        'limite_disponible': limite_disponible,  # Pasamos el límite disponible al template
        'cliente': cliente  # Pasamos el cliente al template
    })



@login_required
def confirmar_operacion(request):
    cliente_activo = get_cliente_activo(request)
    operacion_pendiente = request.session.get('operacion_pendiente')

    if not operacion_pendiente:
        messages.error(request, "No hay una operación pendiente para confirmar.")
        return redirect('core:iniciar_operacion')

    # Convertir montos y tasas de string a Decimal
    for key in ['monto_origen', 'monto_recibido', 'tasa_aplicada', 'comision_aplicada']:
        operacion_pendiente[key] = Decimal(operacion_pendiente[key])

    if request.method == 'POST':
        try:
            moneda_origen_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_origen_codigo'])
            moneda_destino_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_destino_codigo'])
        except Moneda.DoesNotExist:
            messages.error(request, "Error al encontrar las monedas para la transacción.")
            return redirect('core:iniciar_operacion')

        estado_inicial = 'pendiente_pago_cliente' if operacion_pendiente['tipo_operacion'] == 'venta' else 'pendiente_deposito_tauser'
        codigo_operacion_tauser = str(uuid.uuid4())[:10]
        modalidad_tasa = operacion_pendiente.get('modalidad_tasa', 'bloqueada') # Obtener la modalidad de tasa

        # Lógica de Bloqueo de Tasa (GEG-105)
        tasa_garantizada_hasta = None
        # Solo se establece una fecha de expiración si la modalidad es 'bloqueada'
        if modalidad_tasa == 'bloqueada':
            if operacion_pendiente['tipo_operacion'] == 'compra':
                # Cliente vende divisa extranjera, deposita en Tauser. Garantía de 2 horas.
                tasa_garantizada_hasta = timezone.now() + timedelta(hours=2)
            elif operacion_pendiente['tipo_operacion'] == 'venta':
                # Cliente compra divisa extranjera, paga digitalmente. Garantía de 15 minutos.
                tasa_garantizada_hasta = timezone.now() + timedelta(minutes=15)
        # Si la modalidad es 'flotante', tasa_garantizada_hasta permanece como None

        # Obtener el medio de pago de la sesión
        medio_pago_id = operacion_pendiente.get('medio_pago_id')
        medio_pago_obj = None
        if medio_pago_id:
            try:
                medio_pago_obj = TipoMedioPago.objects.get(id_tipo=medio_pago_id)
            except TipoMedioPago.DoesNotExist:
                messages.error(request, "El medio de pago seleccionado ya no es válido.")
                return redirect('core:iniciar_operacion')

        transaccion = Transaccion.objects.create(
            cliente=cliente_activo,
            usuario_operador=request.user,
            tipo_operacion=operacion_pendiente['tipo_operacion'],
            estado=estado_inicial,
            moneda_origen=moneda_origen_obj,
            monto_origen=operacion_pendiente['monto_origen'],
            moneda_destino=moneda_destino_obj,
            monto_destino=operacion_pendiente['monto_recibido'],
            tasa_cambio_aplicada=operacion_pendiente['tasa_aplicada'],
            comision_aplicada=operacion_pendiente['comision_aplicada'],
            codigo_operacion_tauser=codigo_operacion_tauser,
            tasa_garantizada_hasta=tasa_garantizada_hasta,
            modalidad_tasa=modalidad_tasa,
            medio_pago_utilizado=medio_pago_obj, # Guardar el medio de pago
        )
        request.session.pop('operacion_pendiente', None)

        # --- INTEGRACIÓN PASARELA DE PAGO (GEG-112) ---
        # Si la operación es de venta y está pendiente de pago por el cliente,
        # se redirige al detalle de la transacción para que el cliente inicie el pago desde allí.
        if transaccion.tipo_operacion == 'venta' and transaccion.estado == 'pendiente_pago_cliente':
            messages.info(request, "Operación creada. Por favor, procede al pago desde el detalle de la transacción.")
            return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
        
        # --- Flujo original para otros tipos de operación ---
        messages.success(
            request,
            f"Operación {transaccion.id} creada con éxito. Estado: {transaccion.get_estado_display()}. Código: {codigo_operacion_tauser}"
        )
        return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

    return render(request, 'core/confirmar_operacion.html', {'operacion': operacion_pendiente})


@login_required
def detalle_transaccion(request, transaccion_id):
    """
    Muestra los detalles de una transacción creada, incluyendo el código de operación
    y la fecha de expiración de la tasa garantizada, adaptándose al tipo de operación.
    """
    cliente_activo = get_cliente_activo(request)
    transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=cliente_activo)
    return render(request, 'core/detalle_transaccion.html', {'transaccion': transaccion})


@login_required
def historial_transacciones(request):
    """
    Muestra el historial de transacciones del usuario, con opciones de filtrado y paginación.
    """
    cliente_activo = get_cliente_activo(request)

    qs = Transaccion.objects.filter(cliente=cliente_activo)\
         .select_related('moneda_origen', 'moneda_destino')\
         .order_by('-fecha_creacion')

    # --- Filtros (GET) ---
    tipo = request.GET.get('tipo')              # 'compra' | 'venta'
    estado = request.GET.get('estado')          # usa los choices del modelo
    moneda = request.GET.get('moneda')          # código ej. 'USD'
    q = request.GET.get('q')                    # id o código operación
    desde = request.GET.get('desde')            # 'YYYY-MM-DD'
    hasta = request.GET.get('hasta')            # 'YYYY-MM-DD'

    if tipo:
        qs = qs.filter(tipo_operacion=tipo)
    if estado:
        qs = qs.filter(estado=estado)
    if moneda:
        qs = qs.filter(Q(moneda_origen__codigo=moneda) | Q(moneda_destino__codigo=moneda))
    if q:
        qs = qs.filter(Q(id__icontains=q) | Q(codigo_operacion_tauser__icontains=q))

    if desde:
        d = parse_date(desde)
        if d:
            qs = qs.filter(fecha_creacion__date__gte=d)
    if hasta:
        h = parse_date(hasta)
        if h:
            qs = qs.filter(fecha_creacion__date__lte=h)

    # --- Paginación (10 por página) ---
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filtros': {'tipo': tipo, 'estado': estado, 'moneda': moneda, 'q': q, 'desde': desde, 'hasta': hasta},
    }
    return render(request, 'core/historial_transacciones.html', context)
