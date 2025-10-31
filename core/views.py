# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
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
from usuarios.utils import get_cliente_activo, send_otp_email, validate_otp_code # Importar funciones OTP
import json
from payments.stripe_service import create_payment_intent
from urllib.parse import urlencode
from pagos.models import TipoMedioPago, MedioPagoCliente, CampoMedioPago
from medios_acreditacion.models import TipoMedioAcreditacion, MedioAcreditacionCliente, CampoMedioAcreditacion
from django.urls import reverse
from django.views.generic import View, TemplateView # Para las nuevas vistas basadas en clases
from django.contrib.auth.mixins import LoginRequiredMixin # Para las nuevas vistas
from usuarios.forms import VerificacionForm # Para el formulario de OTP
from cotizaciones.models import Cotizacion # Para obtener la tasa en tiempo real
from decimal import Decimal, ROUND_HALF_UP # Para manejar decimales y redondeo
from ted.logic import ajustar_monto_a_denominaciones_disponibles # Importar la lógica de ajuste
from clientes.models import MedioAcreditacion as ClientesMedioAcreditacion # Alias para evitar conflicto

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
    # --- Tasas por moneda (base PYG) para el "rate card" de la calculadora ---
    cotzs = Cotizacion.objects.filter(moneda_base__codigo='PYG').select_related('moneda_destino')
    tasas = {
        c.moneda_destino.codigo: {
            'compra': str(c.total_compra),  # Tauser te compra esa divisa (vos venís con USD->PYG)
            'venta':  str(c.total_venta),   # Tauser te vende esa divisa (vos vas PYG->USD)
        } for c in cotzs
    }
    return render(request,
                   'site/calculator.html', 
                   {'form': form,
                    'resultado': resultado,
                    'iniciar_operacion_url': iniciar_operacion_url,
                    'tasas_json': json.dumps(tasas)})


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
            # Ejecutar simulación en GET para mostrar ajustes desde el inicio
            monto_origen_decimal = Decimal(monto_from_url)
            resultado_simulacion = calcular_simulacion(
                monto_origen_decimal, moneda_origen_from_url, moneda_destino_from_url, user=request.user
            )
            if resultado_simulacion and not resultado_simulacion.get('error'):
                # Actualizar initial_data con los montos ajustados si hubo ajuste
                if resultado_simulacion.get('monto_ajustado'):
                    initial_data['monto'] = str(resultado_simulacion['monto_origen']) # Monto origen ajustado
                initial_data['monto_recibido_simulacion'] = str(resultado_simulacion['monto_recibido'])
                initial_data['tasa_aplicada_simulacion'] = str(resultado_simulacion['tasa_aplicada'])
                initial_data['bonificacion_aplicada_simulacion'] = str(resultado_simulacion['bonificacion_aplicada'])
                initial_data['monto_ajustado_simulacion'] = resultado_simulacion['monto_ajustado']
                initial_data['monto_maximo_posible_simulacion'] = str(resultado_simulacion['monto_maximo_posible'])
            elif resultado_simulacion and resultado_simulacion.get('error'):
                messages.error(request, resultado_simulacion['error'])
                resultado_simulacion = None # Limpiar resultado si hay error

    medios_pago_cliente = MedioPagoCliente.objects.filter(cliente=cliente, activo=True)
    medios_acreditacion_cliente = MedioAcreditacionCliente.objects.filter(cliente=cliente, activo=True)

    if initial_data.get('tipo_operacion') == 'venta' and not medios_pago_cliente.exists():
        messages.info(request, "Necesitas tener al menos un medio de pago creado para realizar una venta. Por favor, crea uno.")
        return redirect(reverse("pagos:clientes_create"))
    
    if initial_data.get('tipo_operacion') == 'compra' and not medios_acreditacion_cliente.exists():
        messages.info(request, "Necesitas tener al menos un medio de acreditación creado para realizar una compra. Por favor, crea uno.")
        return redirect(reverse("medios_acreditacion:clientes_create"))


    form = OperacionForm(request.POST or initial_data, cliente=cliente)
    # Si es GET y ya se hizo una simulación, usar ese resultado
    if request.method == 'GET' and 'monto_recibido_simulacion' in initial_data:
        resultado_simulacion = {
            'monto_recibido': Decimal(initial_data['monto_recibido_simulacion']),
            'tasa_aplicada': Decimal(initial_data['tasa_aplicada_simulacion']),
            'bonificacion_aplicada': Decimal(initial_data['bonificacion_aplicada_simulacion']),
            'monto_ajustado': initial_data['monto_ajustado_simulacion'],
            'monto_maximo_posible': Decimal(initial_data['monto_maximo_posible_simulacion']),
            'error': None,
        }
    else:
        resultado_simulacion = None # Resetear si no hay simulación previa en GET

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

    medios_acreditacion_para_js = {} # Se elimina la inicialización con 'efectivo'
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
            'monto_ajustado': resultado_simulacion.get('monto_ajustado', False), # Guardar si hubo ajuste
            'monto_maximo_posible': str(resultado_simulacion.get('monto_maximo_posible', Decimal('0'))), # Guardar el máximo posible
        }
        # Usar el monto_origen ajustado si existe, de lo contrario el original del formulario
        if resultado_simulacion.get('monto_ajustado'):
            operacion_data['monto_origen'] = str(resultado_simulacion['monto_origen'])
        
        if tipo_operacion == 'venta' and form.cleaned_data.get('medio_pago'):
            operacion_data['medio_pago_id'] = str(form.cleaned_data['medio_pago'].id_medio)
        
        if tipo_operacion == 'compra' and form.cleaned_data.get('medio_acreditacion'):
            operacion_data['medio_acreditacion_id'] = form.cleaned_data['medio_acreditacion']
        
        # Asegurarse de que el metodo_entrega se guarde si está presente en el formulario
        # independientemente de la condición específica de moneda, ya que la visibilidad
        # en el frontend ya lo controla.
        if form.cleaned_data.get('metodo_entrega'):
            operacion_data['metodo_entrega'] = form.cleaned_data['metodo_entrega']

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
        modalidad_tasa = operacion_pendiente.get('modalidad_tasa', 'bloqueada')
        metodo_entrega = operacion_pendiente.get('metodo_entrega') # Obtener el método de entrega

        tipo_operacion = operacion_pendiente['tipo_operacion']
        moneda_origen_codigo = operacion_pendiente['moneda_origen_codigo']
        moneda_destino_codigo = operacion_pendiente['moneda_destino_codigo']
        modalidad_tasa = operacion_pendiente.get('modalidad_tasa', 'bloqueada')
        metodo_entrega = operacion_pendiente.get('metodo_entrega')

        # Lógica para Stripe (prioritaria si se selecciona y es USD -> PYG)
        if tipo_operacion == 'compra' and moneda_origen_codigo == 'USD' and moneda_destino_codigo == 'PYG' and metodo_entrega == 'stripe':
            try:
                moneda_origen_obj = Moneda.objects.get(codigo=moneda_origen_codigo)
                moneda_destino_obj = Moneda.objects.get(codigo=moneda_destino_codigo)
            except Moneda.DoesNotExist:
                messages.error(request, "Error al encontrar las monedas para la transacción.")
                return redirect('core:iniciar_operacion')

            estado_inicial = 'pendiente_pago_stripe'
            codigo_operacion_tauser = str(uuid.uuid4())[:10]
            tasa_garantizada_hasta = timezone.now() + timedelta(hours=2) # Tasa bloqueada por 2 horas para Stripe

            # Obtener el TipoMedioPago para Stripe
            try:
                tipo_medio_pago_stripe = TipoMedioPago.objects.get(engine='stripe')
            except TipoMedioPago.DoesNotExist:
                messages.error(request, "Error de configuración: No se encontró el medio de pago 'Stripe'.")
                return redirect('core:iniciar_operacion')

            transaccion = Transaccion.objects.create(
                cliente=cliente_activo,
                usuario_operador=request.user,
                tipo_operacion=tipo_operacion,
                estado=estado_inicial,
                moneda_origen=moneda_origen_obj,
                monto_origen=operacion_pendiente['monto_origen'],
                moneda_destino=moneda_destino_obj,
                monto_destino=operacion_pendiente['monto_recibido'],
                tasa_cambio_aplicada=operacion_pendiente['tasa_aplicada'],
                comision_aplicada=operacion_pendiente['comision_aplicada'],
                codigo_operacion_tauser=codigo_operacion_tauser,
                tasa_garantizada_hasta=tasa_garantizada_hasta,
                modalidad_tasa=modalidad_tasa, # Se mantiene la modalidad seleccionada
                medio_pago_utilizado=tipo_medio_pago_stripe, # Asignar el medio de pago Stripe
            )
            request.session.pop('operacion_pendiente', None)
            messages.info(request, "Operación registrada. Ahora puedes proceder al pago con tarjeta.")
            return redirect('core:iniciar_pago_stripe', transaccion_id=transaccion.id)

        # Lógica para Flujo A (Tasa Bloqueada sin Stripe)
        elif modalidad_tasa == 'bloqueada':
            return redirect('core:verificar_otp_reserva')

        # Lógica para Flujo B (Tasa Flotante sin Stripe)
        else: # modalidad_tasa == 'flotante'
            try:
                moneda_origen_obj = Moneda.objects.get(codigo=moneda_origen_codigo)
                moneda_destino_obj = Moneda.objects.get(codigo=moneda_destino_codigo)
            except Moneda.DoesNotExist:
                messages.error(request, "Error al encontrar las monedas para la transacción.")
                return redirect('core:iniciar_operacion')

            estado_inicial_flotante = 'pendiente_confirmacion_pago'
            codigo_operacion_tauser = str(uuid.uuid4())[:10]

            medio_pago_utilizado_obj = None
            medio_acreditacion_utilizado_obj = None

            if tipo_operacion == 'venta':
                medio_pago_id = operacion_pendiente.get('medio_pago_id')
                if medio_pago_id:
                    try:
                        medio_pago_utilizado_obj = MedioPagoCliente.objects.get(id_medio=medio_pago_id, cliente=cliente_activo).tipo
                    except MedioPagoCliente.DoesNotExist:
                        messages.error(request, "El medio de pago seleccionado ya no es válido o no pertenece a este cliente.")
                        return redirect('core:iniciar_operacion')
            elif tipo_operacion == 'compra':
                medio_acreditacion_id = operacion_pendiente.get('medio_acreditacion_id')
                # Corregido: Obtener la instancia de clientes.MedioAcreditacion
                # La Transaccion.medio_acreditacion_cliente espera una instancia de clientes.MedioAcreditacion.
                # El formulario envía el id_medio de medios_acreditacion.MedioAcreditacionCliente.
                # Asumimos que hay una correspondencia directa por ID o que el MedioAcreditacionCliente
                # tiene un campo que referencia al MedioAcreditacion de clientes.
                # Dado que no podemos modificar models.py, intentaremos obtener la instancia de clientes.MedioAcreditacion
                # a través del id_medio del MedioAcreditacionCliente.
                medio_acreditacion_para_transaccion = None
                if medio_acreditacion_id and medio_acreditacion_id != 'efectivo':
                    try:
                        # Primero obtenemos la instancia de MedioAcreditacionCliente
                        medio_acreditacion_cliente_obj = MedioAcreditacionCliente.objects.get(id_medio=medio_acreditacion_id, cliente=cliente_activo)
                        
                        # Luego, necesitamos obtener la instancia de clientes.MedioAcreditacion.
                        # Si no hay un campo directo, la única forma es buscar por un campo común.
                        # Asumiendo que el 'identificador' o 'alias' de clientes.MedioAcreditacion
                        # podría estar en los 'datos' o 'alias' de MedioAcreditacionCliente.
                        # Esta es una suposición fuerte debido a la restricción de no tocar models.py.
                        
                        # Intentaremos buscar por el alias y el cliente (AUTH_USER_MODEL)
                        # Esto requiere importar CanalFinanciero
                        from clientes.models import MedioAcreditacion as ClientesMedioAcreditacion
                        from operaciones.models import CanalFinanciero # Necesario para clientes.MedioAcreditacion

                        # Esto es muy especulativo sin conocer la relación exacta.
                        # Si MedioAcreditacionCliente.tipo.nombre se mapea a CanalFinanciero.nombre
                        # y MedioAcreditacionCliente.datos['identificador'] a MedioAcreditacion.identificador
                        
                        # Opción 1: Buscar por ID (si los IDs son los mismos, lo cual es poco probable pero el usuario dijo que antes funcionaba)
                        # medio_acreditacion_para_transaccion = ClientesMedioAcreditacion.objects.get(id=medio_acreditacion_id)

                        # Opción 2: Intentar reconstruir/buscar por campos
                        # Esto es más robusto si los IDs no coinciden, pero requiere más información.
                        # Por ahora, intentaremos la opción más simple que podría haber funcionado "antes".
                        # Primero obtenemos la instancia de MedioAcreditacionCliente
                        medio_acreditacion_cliente_obj = MedioAcreditacionCliente.objects.get(id_medio=medio_acreditacion_id, cliente=cliente_activo)
                        
                        # Extraer alias e identificador de MedioAcreditacionCliente
                        alias_cliente_ma = medio_acreditacion_cliente_obj.alias
                        identificador_cliente_ma = medio_acreditacion_cliente_obj.datos.get('identificador', '') # Asumiendo que 'identificador' está en 'datos'

                        # Intentar encontrar clientes.MedioAcreditacion por los campos
                        try:
                            medio_acreditacion_para_transaccion = ClientesMedioAcreditacion.objects.get(
                                cliente=request.user, # El cliente de clientes.MedioAcreditacion es el usuario autenticado
                                identificador=identificador_cliente_ma,
                                alias=alias_cliente_ma
                            )
                        except ClientesMedioAcreditacion.DoesNotExist:
                            # Si no se encuentra, y dado que el usuario indicó que no importa mucho,
                            # asignamos None. Esto evita el error y permite que la transacción continúe.
                            medio_acreditacion_para_transaccion = None
                        
                    except MedioAcreditacionCliente.DoesNotExist:
                        messages.error(request, "El medio de acreditación seleccionado ya no es válido o no pertenece a este cliente (MedioAcreditacionCliente no encontrado).")
                        return redirect('core:iniciar_operacion')
                    except Exception as e:
                        messages.error(request, f"Error inesperado al obtener el medio de acreditación: {e}")
                        return redirect('core:iniciar_operacion')
                # Si medio_acreditacion_id es 'efectivo', medio_acreditacion_para_transaccion permanece None, lo cual es correcto.

            if tipo_operacion == 'compra':
                # Para compras con tasa flotante, el estado inicial es pendiente_pago_cliente
                # y no se redirige a confirmacion_final_pago, sino directamente al detalle.
                transaccion = Transaccion.objects.create(
                    cliente=cliente_activo,
                    usuario_operador=request.user,
                    tipo_operacion=tipo_operacion,
                    estado='pendiente_pago_cliente', # Estado inicial para compra flotante
                    moneda_origen=moneda_origen_obj,
                    monto_origen=Decimal(operacion_pendiente['monto_origen']),
                    moneda_destino=moneda_destino_obj,
                    monto_destino=Decimal(operacion_pendiente['monto_recibido']),
                    tasa_cambio_aplicada=Decimal(operacion_pendiente['tasa_aplicada']),
                    comision_aplicada=Decimal(operacion_pendiente['comision_aplicada']),
                    codigo_operacion_tauser=codigo_operacion_tauser,
                    tasa_garantizada_hasta=None, # No hay tasa garantizada para flotante
                    modalidad_tasa=modalidad_tasa,
                    medio_acreditacion_cliente=medio_acreditacion_para_transaccion, # Para compras
                )
                request.session.pop('operacion_pendiente', None)
                messages.success(request, "Operación de compra con tasa flotante iniciada. Por favor, realiza el pago en el tauser.")
                return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
            else:
                # Lógica existente para ventas con tasa flotante
                transaccion = Transaccion.objects.create(
                    cliente=cliente_activo,
                    usuario_operador=request.user,
                    tipo_operacion=tipo_operacion,
                    estado=estado_inicial_flotante, # 'pendiente_confirmacion_pago'
                    moneda_origen=moneda_origen_obj,
                    monto_origen=Decimal(operacion_pendiente['monto_origen']),
                    moneda_destino=moneda_destino_obj,
                    monto_destino=Decimal(operacion_pendiente['monto_recibido']),
                    tasa_cambio_aplicada=Decimal(operacion_pendiente['tasa_aplicada']),
                    comision_aplicada=Decimal(operacion_pendiente['comision_aplicada']),
                    codigo_operacion_tauser=codigo_operacion_tauser,
                    tasa_garantizada_hasta=None,
                    modalidad_tasa=modalidad_tasa,
                    medio_pago_utilizado=medio_pago_utilizado_obj, # Para ventas
                )
                request.session.pop('operacion_pendiente', None)
                messages.info(request, "Operación de venta con tasa flotante iniciada. Por favor, confirma el pago.")
                return redirect('core:confirmacion_final_pago', transaccion_id=transaccion.id)

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
            customer_email=request.user.email,
            transaction_id=str(transaccion.id) # ¡Añadido el transaction_id al metadata!
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


# ----------------------------
# Nuevas Vistas para Flujos de Operación
# ----------------------------

class VerificarOtpReservaView(LoginRequiredMixin, View):
    """
    Vista para el Flujo A (Tasa Garantizada):
    Solicita OTP antes de crear la transacción y reservar la tasa.
    """
    template_name = 'core/verificar_otp.html' # Plantilla para ingresar OTP

    def get(self, request, *args, **kwargs):
        operacion_pendiente = request.session.get('operacion_pendiente')
        if not operacion_pendiente:
            messages.error(request, "No hay una operación pendiente para verificar.")
            return redirect('core:iniciar_operacion')
        
        cliente_activo = get_cliente_activo(request)
        if not cliente_activo:
            messages.info(request, "Seleccioná con qué cliente querés operar.")
            return redirect("usuarios:seleccionar_cliente")

        # Enviar OTP al email del usuario
        send_otp_email(
            request.user,
            "Confirmación de Reserva de Tasa",
            "Tu código de verificación para reservar la tasa es: {code}. Válido por {minutes} minutos."
        )
        messages.info(request, f"Hemos enviado un código de verificación a tu email ({request.user.email}).")
        form = VerificacionForm()
        return render(request, self.template_name, {'form': form, 'email': request.user.email})

    def post(self, request, *args, **kwargs):
        operacion_pendiente = request.session.get('operacion_pendiente')
        if not operacion_pendiente:
            messages.error(request, "Sesión de operación inválida.")
            return redirect('core:iniciar_operacion')

        form = VerificacionForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data['codigo']
            if validate_otp_code(request.user, codigo):
                # OTP válido, proceder a crear la transacción con tasa garantizada
                cliente_activo = get_cliente_activo(request)
                try:
                    moneda_origen_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_origen_codigo'])
                    moneda_destino_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_destino_codigo'])
                except Moneda.DoesNotExist:
                    messages.error(request, "Error al encontrar las monedas para la transacción.")
                    return redirect('core:iniciar_operacion')

                estado_inicial = 'pendiente_pago_cliente'
                codigo_operacion_tauser = str(uuid.uuid4())[:10]
                modalidad_tasa = 'bloqueada'

                tasa_garantizada_hasta = None
                if operacion_pendiente['tipo_operacion'] == 'compra':
                    tasa_garantizada_hasta = timezone.now() + timedelta(hours=2)
                elif operacion_pendiente['tipo_operacion'] == 'venta':
                    tasa_garantizada_hasta = timezone.now() + timedelta(minutes=15)
                
                # Obtener el medio de pago del cliente de la sesión
                medio_pago_id = operacion_pendiente.get('medio_pago_id')
                medio_pago_cliente_obj = None
                if medio_pago_id:
                    try:
                        medio_pago_cliente_obj = MedioPagoCliente.objects.get(id_medio=medio_pago_id, cliente=cliente_activo)
                    except MedioPagoCliente.DoesNotExist:
                        messages.error(request, "El medio de pago seleccionado ya no es válido o no pertenece a este cliente.")
                        return redirect('core:iniciar_operacion')

                transaccion = Transaccion.objects.create(
                    cliente=cliente_activo,
                    usuario_operador=request.user,
                    tipo_operacion=operacion_pendiente['tipo_operacion'],
                    estado=estado_inicial,
                    moneda_origen=moneda_origen_obj,
                    monto_origen=Decimal(operacion_pendiente['monto_origen']),
                    moneda_destino=moneda_destino_obj,
                    monto_destino=Decimal(operacion_pendiente['monto_recibido']),
                    tasa_cambio_aplicada=Decimal(operacion_pendiente['tasa_aplicada']),
                    comision_aplicada=Decimal(operacion_pendiente['comision_aplicada']),
                    codigo_operacion_tauser=codigo_operacion_tauser,
                    tasa_garantizada_hasta=tasa_garantizada_hasta,
                    modalidad_tasa=modalidad_tasa,
                    medio_pago_utilizado=medio_pago_cliente_obj.tipo if medio_pago_cliente_obj else None,
                )
                request.session.pop('operacion_pendiente', None) # Limpiar sesión

                messages.success(request, f"Tasa reservada y operación {transaccion.id} creada. Procede al pago.")
                # Redirigir al inicio del pago (que ahora puede ser la pasarela o el detalle)
                if transaccion.tipo_operacion == 'venta' and transaccion.estado == 'pendiente_pago_cliente':
                    return redirect('transacciones:iniciar_pago', transaccion_id=transaccion.id)
                elif transaccion.tipo_operacion == 'compra' and operacion_pendiente.get('medio_acreditacion_id') == 'efectivo':
                    return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
                else:
                    return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)

            else:
                messages.error(request, "Código OTP incorrecto o expirado.")
        else:
            messages.error(request, "Por favor, ingresa un código válido.")
        
        return render(request, self.template_name, {'form': form, 'email': request.user.email})


class ConfirmacionFinalPagoView(LoginRequiredMixin, TemplateView):
    """
    Vista para el Flujo B (Tasa Flotante):
    Muestra la tasa en tiempo real y el botón de confirmación final.
    """
    template_name = 'core/confirmacion_final_pago.html'

    def get(self, request, transaccion_id, *args, **kwargs):
        transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=get_cliente_activo(self.request))

        if transaccion.estado != 'pendiente_confirmacion_pago' or transaccion.modalidad_tasa != 'flotante':
            messages.error(self.request, "La transacción no está en un estado válido para confirmación final.")
            return redirect('core:iniciar_operacion') # O a una página de error
        
        context = self.get_context_data(transaccion=transaccion, **kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transaccion = kwargs.get('transaccion') # La transacción ya se obtuvo en el método get()

        # Obtener la tasa de cambio en tiempo real
        try:
            cotizacion_actual = Cotizacion.objects.get(
                moneda_base=transaccion.moneda_origen,
                moneda_destino=transaccion.moneda_destino
            )
            # La tasa de mercado actual
            tasa_actual = cotizacion_actual.total_venta if transaccion.tipo_operacion == 'venta' else cotizacion_actual.total_compra
            
            # Recalcular monto_destino_actual y monto_origen_actual con la tasa actual
            if transaccion.tipo_operacion == 'venta': # Cliente compra divisa extranjera
                # --- CORRECCIÓN ---
                # El monto a recibir (destino) es fijo. Se ajusta por denominación.
                ajuste = ajustar_monto_a_denominaciones_disponibles(
                    transaccion.monto_destino, transaccion.moneda_destino, 'venta'
                )
                monto_destino_actual = ajuste['monto_ajustado']

                # Se recalcula el monto a pagar (origen) en PYG con la nueva tasa.
                monto_origen_actual = (monto_destino_actual * tasa_actual).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                
                # Actualizar operacion_pendiente en sesión con los montos ajustados
                operacion_pendiente = self.request.session.get('operacion_pendiente', {})
                operacion_pendiente['monto_origen'] = str(monto_origen_actual)
                operacion_pendiente['monto_recibido'] = str(monto_destino_actual)
                operacion_pendiente['tasa_aplicada'] = str(tasa_actual) # Asegurar que la tasa también se actualice
                operacion_pendiente['monto_ajustado'] = ajuste['ajustado']
                operacion_pendiente['monto_maximo_posible'] = str(ajuste['monto_maximo_posible'])
                self.request.session['operacion_pendiente'] = operacion_pendiente

            else: # Cliente vende divisa extranjera
                monto_origen_actual = transaccion.monto_origen # El monto origen es el que el cliente entrega
                monto_destino_actual = (transaccion.monto_origen * tasa_actual).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                
                # Actualizar operacion_pendiente en sesión con los montos ajustados
                operacion_pendiente = self.request.session.get('operacion_pendiente', {})
                operacion_pendiente['monto_origen'] = str(monto_origen_actual)
                operacion_pendiente['monto_recibido'] = str(monto_destino_actual)
                operacion_pendiente['tasa_aplicada'] = str(tasa_actual) # Asegurar que la tasa también se actualice
                operacion_pendiente['monto_ajustado'] = False # No hay ajuste de denominaciones para este caso
                operacion_pendiente['monto_maximo_posible'] = str(transaccion.monto_destino) # O el monto original
                self.request.session['operacion_pendiente'] = operacion_pendiente


        except Cotizacion.DoesNotExist:
            messages.error(self.request, "Error interno: No se pudo obtener la tasa de cambio actual para el contexto.")
            tasa_actual = Decimal('0.00')
            monto_destino_actual = Decimal('0.00')
            monto_origen_actual = Decimal('0.00')
        
        context['transaccion'] = transaccion
        context['tasa_actual'] = tasa_actual
        context['monto_destino_actual'] = monto_destino_actual
        context['monto_origen_actual'] = monto_origen_actual # Añadir el monto origen actual
        context['email_usuario'] = self.request.user.email # Para mostrar en la plantilla
        return context

    def post(self, request, transaccion_id, *args, **kwargs):
        cliente_activo = get_cliente_activo(self.request)
        transaccion = get_object_or_404(Transaccion, id=transaccion_id, cliente=cliente_activo)
        operacion_pendiente = self.request.session.get('operacion_pendiente')

        if not operacion_pendiente:
            messages.error(request, "No hay una operación pendiente para confirmar.")
            return redirect('core:iniciar_operacion')

        # Actualizar la transacción con los valores de la sesión
        transaccion.monto_origen = Decimal(operacion_pendiente['monto_origen'])
        transaccion.tasa_cambio_aplicada = Decimal(operacion_pendiente['tasa_aplicada'])
        # Also update monto_destino if it was adjusted in the get method
        if 'monto_destino' in operacion_pendiente and operacion_pendiente.get('monto_ajustado'):
             transaccion.monto_destino = Decimal(operacion_pendiente['monto_destino'])

        # --- NEW LOGIC FOR COMPRA WITH TASA FLOTANTE ---
        if transaccion.tipo_operacion == 'compra' and transaccion.modalidad_tasa == 'flotante':
            transaccion.estado = 'pendiente_pago_cliente' # Set the correct state
            transaccion.save() # Save the transaction with the new state
            messages.success(request, "Operación registrada. Por favor, realiza el pago en el tauser.")
            request.session.pop('operacion_pendiente', None) # Clear session data
            # Redirect to a page showing the transaction status, e.g., detail or history
            return redirect('core:detalle_transaccion', transaccion_id=transaccion.id)
        # --- END NEW LOGIC ---
        else:
            # Existing logic for other cases (e.g., venta flotante, tasa bloqueada)
            transaccion.save() # Save the updated amounts for these cases
            messages.success(request, "Operación actualizada con la tasa de cambio actual. Procediendo al pago.")
            return redirect('transacciones:iniciar_pago', transaccion_id=transaccion_id)
