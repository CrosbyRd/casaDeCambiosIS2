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
from decimal import Decimal # Para manejar decimales

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
                tipo_operacion=tipo_operacion,
                estado=estado_inicial_flotante,
                moneda_origen=moneda_origen_obj,
                monto_origen=operacion_pendiente['monto_origen'],
                moneda_destino=moneda_destino_obj,
                monto_destino=operacion_pendiente['monto_recibido'],
                tasa_cambio_aplicada=operacion_pendiente['tasa_aplicada'],
                comision_aplicada=operacion_pendiente['comision_aplicada'],
                codigo_operacion_tauser=codigo_operacion_tauser,
                tasa_garantizada_hasta=None,
                modalidad_tasa=modalidad_tasa,
                medio_pago_utilizado=medio_pago_cliente_obj.tipo if medio_pago_cliente_obj else None,
            )
            request.session.pop('operacion_pendiente', None)

            messages.info(request, "Operación iniciada con tasa flotante. Por favor, confirma el pago.")
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
            tasa_actual = cotizacion_actual.total_venta # Asumiendo que es una venta de divisa (cliente compra)
            monto_destino_actual = transaccion.monto_origen / tasa_actual
        except Cotizacion.DoesNotExist:
            # Este caso ya debería ser manejado en el método get()
            # Si llega aquí, es un error inesperado o un estado inconsistente
            messages.error(self.request, "Error interno: No se pudo obtener la tasa de cambio actual para el contexto.")
            tasa_actual = Decimal('0.00') # Valor por defecto para evitar errores
            monto_destino_actual = Decimal('0.00') # Valor por defecto para evitar errores
        
        context['transaccion'] = transaccion
        context['tasa_actual'] = tasa_actual
        context['monto_destino_actual'] = monto_destino_actual
        context['email_usuario'] = self.request.user.email # Para mostrar en la plantilla
        return context

    def post(self, request, transaccion_id, *args, **kwargs):
        # Este POST solo redirige a la vista de inicio de pago en transacciones
        # La lógica de MFA y actualización de tasa se manejará en IniciarPagoTransaccionView
        return redirect('transacciones:iniciar_pago', transaccion_id=transaccion_id)
