from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.urls import reverse

from .forms import SimulacionForm, OperacionForm
from .logic import calcular_simulacion
from monedas.models import Moneda
from cotizaciones.models import Cotizacion
from transacciones.models import Transaccion
from clientes.models import Cliente
import uuid
from core.utils import validar_limite_transaccion


def calculadora_view(request):
    form = SimulacionForm(request.POST or None)
    resultado = None

    if request.method == 'POST' and form.is_valid():
        monto_origen = form.cleaned_data['monto']
        moneda_origen = form.cleaned_data['moneda_origen']
        moneda_destino = form.cleaned_data['moneda_destino']

        resultado = calcular_simulacion(monto_origen, moneda_origen, moneda_destino, user=request.user)

        if resultado['error']:
            messages.error(request, resultado['error'])
            resultado = None

    iniciar_operacion_url = request.build_absolute_uri(reverse('core:iniciar_operacion'))
    return render(request, 'site/calculator.html', {'form': form, 'resultado': resultado, 'iniciar_operacion_url': iniciar_operacion_url})


def site_rates(request):
    cotizaciones = Cotizacion.objects.all().select_related('moneda_base', 'moneda_destino')
    return render(request, 'site/rates.html', {'cotizaciones': cotizaciones})


@login_required
def iniciar_operacion(request):
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

    form = OperacionForm(request.POST or initial_data)
    resultado_simulacion = None

    if request.method == 'POST' and form.is_valid():
        tipo_operacion = form.cleaned_data['tipo_operacion']
        monto_origen = form.cleaned_data['monto']
        moneda_origen_codigo = form.cleaned_data['moneda_origen']
        moneda_destino_codigo = form.cleaned_data['moneda_destino']

        try:
            moneda_origen_obj = Moneda.objects.get(codigo=moneda_origen_codigo)
            moneda_destino_obj = Moneda.objects.get(codigo=moneda_destino_codigo)
        except Moneda.DoesNotExist as e:
            messages.error(request, f"Error: {e}")
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        resultado_simulacion = calcular_simulacion(
            monto_origen, moneda_origen_codigo, moneda_destino_codigo, user=request.user
        )

        if resultado_simulacion['error']:
            messages.error(request, resultado_simulacion['error'])
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        cliente = request.user.clientes.first()
        if not cliente:
            messages.error(request, "No se encontró un perfil de cliente asociado a tu usuario.")
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        # --- Validación de límites usando la función existente ---
        if tipo_operacion == 'compra':
            monto_a_validar = monto_origen
            moneda_a_validar = moneda_origen_codigo
        else:  # venta
            monto_a_validar = resultado_simulacion['monto_recibido']
            moneda_a_validar = moneda_destino_codigo

        usuario = request.user  # CustomUser
        valido, mensaje = validar_limite_transaccion(
            request.user,
            monto_a_validar,
            moneda_origen=moneda_a_validar,
            moneda_destino=moneda_destino_codigo
        )



        if not valido:
            messages.error(request, mensaje)
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        # --- Proceder a confirmación ---
        request.session['operacion_pendiente'] = {
            'tipo_operacion': tipo_operacion,
            'moneda_origen_codigo': moneda_origen_codigo,
            'monto_origen': str(monto_origen),
            'moneda_destino_codigo': moneda_destino_codigo,
            'monto_recibido': str(resultado_simulacion['monto_recibido']),
            'tasa_aplicada': str(resultado_simulacion['tasa_aplicada']),
            'comision_aplicada': str(resultado_simulacion['bonificacion_aplicada']),
        }
        return redirect('core:confirmar_operacion')

    return render(request, 'core/iniciar_operacion.html', {'form': form, 'resultado_simulacion': resultado_simulacion})


@login_required
def confirmar_operacion(request):
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

        transaccion = Transaccion.objects.create(
            cliente=request.user,
            tipo_operacion=operacion_pendiente['tipo_operacion'],
            estado=estado_inicial,
            moneda_origen=moneda_origen_obj,
            monto_origen=operacion_pendiente['monto_origen'],
            moneda_destino=moneda_destino_obj,
            monto_destino=operacion_pendiente['monto_recibido'],
            tasa_cambio_aplicada=operacion_pendiente['tasa_aplicada'],
            comision_aplicada=operacion_pendiente['comision_aplicada'],
            codigo_operacion_tauser=codigo_operacion_tauser,
        )
        messages.success(
            request,
            f"Operación {transaccion.id} creada con éxito. Estado: {transaccion.get_estado_display()}. Código: {codigo_operacion_tauser}"
        )
        request.session.pop('operacion_pendiente', None)
        return redirect('usuarios:dashboard')

    return render(request, 'core/confirmar_operacion.html', {'operacion': operacion_pendiente})
