# core/views.py
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
import json
from payments.stripe_service import create_payment_intent
from urllib.parse import urlencode
from pagos.models import TipoMedioPago, MedioPagoCliente, CampoMedioPago
from medios_acreditacion.models import TipoMedioAcreditacion, MedioAcreditacionCliente, CampoMedioAcreditacion
from django.urls import reverse

def calculadora_view(request):
    form = SimulacionForm(request.POST or None)
    resultado = None

    if request.method == 'POST' and form.is_valid():
        monto_origen = form.cleaned_data['monto']
        moneda_origen = form.cleaned_data['moneda_origen']
        moneda_destino = form.cleaned_data['moneda_destino']

        if 'proceder' in request.POST:
            import urllib.parse
            query_params = {
                'monto': monto_origen,
                'moneda_origen': moneda_origen,
                'moneda_destino': moneda_destino,
            }
            redirect_url = f"{reverse('core:iniciar_operacion')}?{urllib.parse.urlencode(query_params)}"
            return redirect(redirect_url)

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
    cliente = get_cliente_activo(request)
    if not cliente:
        messages.info(request, "Seleccioná con qué cliente querés operar.")
        return redirect("usuarios:seleccionar_cliente")

    initial_data = {}

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

    medios_pago_cliente = MedioPagoCliente.objects.filter(cliente=cliente, activo=True)
    medios_acreditacion_cliente = MedioAcreditacionCliente.objects.filter(cliente=cliente, activo=True)

    if initial_data.get('tipo_operacion') == 'venta' and not medios_pago_cliente.exists():
        messages.info(request, "Necesitas tener al menos un medio de pago creado para realizar una venta. Por favor, crea uno.")
        return redirect(reverse("pagos:clientes_create"))
    
    if initial_data.get('tipo_operacion') == 'compra' and not medios_acreditacion_cliente.exists():
        messages.info(request, "Necesitas tener al menos un medio de acreditación creado para realizar una compra, o seleccionar 'Efectivo'. Por favor, crea uno.")
        return redirect(reverse("medios_acreditacion:clientes_create"))


    form = OperacionForm(request.POST or initial_data, cliente=cliente)
    resultado_simulacion = None

    medios_pago_para_js = {}
    for medio in medios_pago_cliente.prefetch_related('tipo__campos').all():
        campos_data = []
        for campo in medio.tipo.campos.filter(activo=True):
            campos_data.append({
                'nombre_campo': campo.nombre_campo,
                'valor': medio.datos.get(campo.nombre_campo, ''),
            })
        medios_pago_para_js[str(medio.id_medio)] = {
            'id_medio': str(medio.id_medio),
            'alias': medio.alias,
            'tipo_nombre': medio.tipo.nombre,
            'campos': campos_data,
        }
    medios_pago_json = json.dumps(medios_pago_para_js)

    medios_acreditacion_para_js = {
        'efectivo': {
            'id_medio': 'efectivo',
            'alias': 'Efectivo',
            'tipo_nombre': 'Retiro en Tauser',
            'campos': [],
        }
    }
    for medio in medios_acreditacion_cliente.prefetch_related('tipo__campos').all():
        campos_data = []
        for campo in medio.tipo.campos.filter(activo=True):
            campos_data.append({
                'nombre_campo': campo.nombre,
                'valor': medio.datos.get(campo.nombre, ''),
            })
        medios_acreditacion_para_js[str(medio.id_medio)] = {
            'id_medio': str(medio.id_medio),
            'alias': medio.alias,
            'tipo_nombre': medio.tipo.nombre,
            'campos': campos_data,
        }
    medios_acreditacion_json = json.dumps(medios_acreditacion_para_js)

    limite_cfg = TransactionLimit.objects.filter(moneda__codigo='PYG').first()
    limite_disponible = Decimal(limite_cfg.monto_diario) if limite_cfg else Decimal(0)
    hoy = now().date()
    total_transacciones_hoy = Transaccion.objects.filter(
        cliente=cliente,
        fecha_creacion__date=hoy
    ).aggregate(Sum('monto_origen'))['monto_origen__sum'] or Decimal(0)
    limite_disponible -= total_transacciones_hoy

    if request.method == 'POST' and form.is_valid():
        tipo_operacion = form.cleaned_data['tipo_operacion']
        monto_origen = form.cleaned_data['monto']
        moneda_origen_codigo = form.cleaned_data['moneda_origen']
        moneda_destino_codigo = form.cleaned_data['moneda_destino']

        resultado_simulacion = calcular_simulacion(monto_origen, moneda_origen_codigo, moneda_destino_codigo, user=request.user)

        if resultado_simulacion.get('error'):
            messages.error(request, resultado_simulacion['error'])
            return render(request, 'core/iniciar_operacion.html', {'form': form, 'cliente': cliente})

        if monto_origen > limite_disponible:
            messages.error(request, f"El monto excede el límite disponible de {limite_disponible} PYG.")
            return render(request, 'core/iniciar_operacion.html', {'form': form, 'cliente': cliente})

        operacion_data = {
            'tipo_operacion': tipo_operacion,
            'moneda_origen_codigo': moneda_origen_codigo,
            'monto_origen': str(monto_origen),
            'moneda_destino_codigo': moneda_destino_codigo,
            'monto_recibido': str(resultado_simulacion['monto_recibido']),
            'tasa_aplicada': str(resultado_simulacion['tasa_aplicada']),
            'comision_aplicada': str(resultado_simulacion['bonificacion_aplicada']),
            'modalidad_tasa': form.cleaned_data['modalidad_tasa'],
        }
        if tipo_operacion == 'venta' and form.cleaned_data.get('medio_pago'):
            operacion_data['medio_pago_id'] = str(form.cleaned_data['medio_pago'].id_medio)
        
        if tipo_operacion == 'compra' and form.cleaned_data.get('medio_acreditacion'):
            operacion_data['medio_acreditacion_id'] = form.cleaned_data['medio_acreditacion']
        
        if tipo_operacion == 'compra' and moneda_origen_codigo == 'USD' and moneda_destino_codigo == 'PYG':
            operacion_data['metodo_entrega'] = form.cleaned_data.get('metodo_entrega')

        request.session['operacion_pendiente'] = operacion_data
        return redirect('core:confirmar_operacion')

    return render(request, 'core/iniciar_operacion.html', {
        'form': form,
        'resultado_simulacion': resultado_simulacion,
        'limite_disponible': limite_disponible,
        'cliente': cliente,
        'medios_pago_json': medios_pago_json,
        'medios_acreditacion_json': medios_acreditacion_json,
    })

@login_required
def confirmar_operacion(request):
    cliente_activo = get_cliente_activo(request)
    operacion_pendiente = request.session.get('operacion_pendiente')

    if not operacion_pendiente:
        messages.error(request, "No hay una operación pendiente para confirmar.")
        return redirect('core:iniciar_operacion')

    for key in ['monto_origen', 'monto_recibido', 'tasa_aplicada', 'comision_aplicada']:
        operacion_pendiente[key] = Decimal(operacion_pendiente[key])

    if request.method == 'POST':
        try:
            moneda_origen_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_origen_codigo'])
            moneda_destino_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_destino_codigo'])
        except Moneda.DoesNotExist:
            messages.error(request, "Error al encontrar las monedas para la transacción.")
            return redirect('core:iniciar_operacion')
        
        metodo_entrega = operacion_pendiente.get('metodo_entrega')
        estado_inicial = 'pendiente_deposito_tauser'

        if operacion_pendiente['tipo_operacion'] == 'venta':
            estado_inicial = 'pendiente_pago_cliente'
        elif metodo_entrega == 'stripe':
            estado_inicial = 'pendiente_pago_stripe'
        
        codigo_operacion_tauser = str(uuid.uuid4())[:10]
        modalidad_tasa = operacion_pendiente.get('modalidad_tasa', 'bloqueada')
        tasa_garantizada_hasta = None

        if modalidad_tasa == 'bloqueada':
            if operacion_pendiente['tipo_operacion'] == 'compra':
                tasa_garantizada_hasta = timezone.now() + timedelta(hours=2)
            elif operacion_pendiente['tipo_operacion'] == 'venta':
                tasa_garantizada_hasta = timezone.now() + timedelta(minutes=15)

        medio_pago_id = operacion_pendiente.get('medio_pago_id')
        medio_pago_cliente_obj = None
        if medio_pago_id:
            try:
                medio_pago_cliente_obj = MedioPagoCliente.objects.get(id_medio=medio_pago_id, cliente=cliente_activo)
            except MedioPagoCliente.DoesNotExist:
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
            medio_pago_utilizado=medio_pago_cliente_obj.tipo if medio_pago_cliente_obj else None,
        )
        request.session.pop('operacion_pendiente', None)
        
        if metodo_entrega == 'stripe':
             messages.info(request, "Operación registrada. Ahora puedes proceder al pago con tarjeta.")
             return redirect('core:iniciar_pago_stripe', transaccion_id=transaccion.id)
        
        if transaccion.tipo_operacion == 'compra' and operacion_pendiente.get('medio_acreditacion_id') == 'efectivo':
            messages.info(request, "Operación creada. Espera la confirmación para el retiro en efectivo.")
            return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

        if transaccion.tipo_operacion == 'venta' and transaccion.estado == 'pendiente_pago_cliente':
            messages.info(request, "Operación creada. Procede al pago desde el detalle de la transacción.")
            return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
        
        messages.success(
            request,
            f"Operación {transaccion.id} creada con éxito. Estado: {transaccion.get_estado_display()}. Código: {codigo_operacion_tauser}"
        )
        return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

    return render(request, 'core/confirmar_operacion.html', {'operacion': operacion_pendiente})


@login_required
def detalle_transaccion(request, transaccion_id):
    cliente_activo = get_cliente_activo(request)
    transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=cliente_activo)
    return render(request, 'core/detalle_transaccion.html', {'transaccion': transaccion})


@login_required
def historial_transacciones(request):
    cliente_activo = get_cliente_activo(request)
    qs = Transaccion.objects.filter(cliente=cliente_activo)\
         .select_related('moneda_origen', 'moneda_destino')\
         .order_by('-fecha_creacion')

    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')
    moneda = request.GET.get('moneda')
    q = request.GET.get('q')
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')

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

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filtros': {'tipo': tipo, 'estado': estado, 'moneda': moneda, 'q': q, 'desde': desde, 'hasta': hasta},
    }
    return render(request, 'core/historial_transacciones.html', context)


# --- VISTA MODIFICADA ---
@login_required
def iniciar_pago_stripe(request, transaccion_id):
    """
    Esta vista actúa como un puente:
    1. Crea el Payment Intent usando tu servicio de la app 'payments'.
    2. Redirige a la página de pago de Stripe de la app 'payments' con los datos necesarios.
    """
    cliente_activo = get_cliente_activo(request)
    transaccion = get_object_or_404(
        Transaccion, 
        id=transaccion_id, 
        cliente=cliente_activo,
        estado='pendiente_pago_stripe'
    )

    try:
        monto_en_centavos = int(transaccion.monto_origen * 100)
        moneda = transaccion.moneda_origen.codigo.lower()
        
        # --- CORREGIDO: Se ajustan los nombres de los argumentos ---
        payment_intent_data = create_payment_intent(
            amount_in_cents=monto_en_centavos, # Argumento correcto
            currency=moneda,
            customer_email=request.user.email
        )
        
        # --- CORREGIDO: Se usa la clave 'clientSecret' que devuelve tu servicio ---
        client_secret = payment_intent_data.get('clientSecret') 
        if not client_secret:
            raise Exception("No se pudo obtener el client_secret de Stripe.")

        base_url = reverse('payments:stripe_payment_page')
        params = urlencode({
            'client_secret': client_secret,
            'transaction_id': str(transaccion.id),
        })
        redirect_url = f'{base_url}?{params}'
        
        return redirect(redirect_url)

    except Exception as e:
        messages.error(request, f"Hubo un error al iniciar el proceso de pago: {e}")
        return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)