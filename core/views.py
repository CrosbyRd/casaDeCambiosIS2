from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.urls import reverse
from django.utils.http import urlencode

from .forms import SimulacionForm, OperacionForm # Importar OperacionForm
from .logic import calcular_simulacion
from monedas.models import Moneda
from cotizaciones.models import Cotizacion
from transacciones.models import Transaccion
from clientes.models import Cliente # Importar Cliente para límites
from decimal import Decimal
import uuid

# Función auxiliar para obtener el límite de transacción (simulado por ahora)
def obtener_limite_transaccion(cliente, moneda, tipo_operacion):
    """
    Esta función simula la obtención del límite de transacción para un cliente,
    una moneda y un tipo de operación dados. En el futuro, esta función se
    reemplazará con la lógica real para obtener los límites de la configuración
    (GEG-103).

    IMPORTANTE: Esta función DEBE ser reemplazada con la implementación real
    de la historia de usuario GEG-103 para que los límites transaccionales
    se apliquen correctamente.
    """
    # Por ahora, devolvemos un límite fijo muy alto para que la validación siempre pase.
    return Decimal('1000000000.00') # Un billón

# La calculadora debe ser accesible para todos, con o sin sesión iniciada.
# Las bonificaciones se aplicarán si el usuario está autenticado.
def calculadora_view(request):
    form = SimulacionForm(request.POST or None)
    resultado = None

    if request.method == 'POST' and form.is_valid():
        monto_origen = form.cleaned_data['monto']
        moneda_origen = form.cleaned_data['moneda_origen']
        moneda_destino = form.cleaned_data['moneda_destino']

        # Pasar el usuario a la lógica de simulación para aplicar bonificaciones
        resultado = calcular_simulacion(monto_origen, moneda_origen, moneda_destino, user=request.user)

        if resultado['error']:
            messages.error(request, resultado['error'])
            resultado = None  # Limpiar resultado si hay error para no mostrar datos incorrectos

    iniciar_operacion_url = request.build_absolute_uri(reverse('core:iniciar_operacion'))
    return render(request, 'site/calculator.html', {'form': form, 'resultado': resultado, 'iniciar_operacion_url': iniciar_operacion_url})


def site_rates(request):
    """
    Vista para mostrar los tipos de cambio actuales.
    """
    cotizaciones = Cotizacion.objects.all().select_related('moneda_base', 'moneda_destino')
    return render(request, 'site/rates.html', {'cotizaciones': cotizaciones})


@login_required
def iniciar_operacion(request):
    form = OperacionForm(request.POST or None)
    resultado_simulacion = None

    if request.method == 'POST' and form.is_valid():
        monto_origen = form.cleaned_data['monto']
        moneda_origen = form.cleaned_data['moneda_origen']
        moneda_destino = form.cleaned_data['moneda_destino']
        
        # Pasar el usuario a la lógica de simulación para aplicar bonificaciones
        resultado = calcular_simulacion(monto_origen, moneda_origen, moneda_destino, user=request.user)
        
        if resultado['error']:
            messages.error(request, resultado['error'])
            resultado = None # Limpiar resultado si hay error para no mostrar datos incorrectos
    
    return render(request, 'site/calculator.html', {'form': form, 'resultado': resultado})


@login_required
def iniciar_operacion(request):
    initial_data = {}
    if request.method == 'GET':
        # Intentar pre-llenar el formulario con datos de la calculadora si vienen en la URL
        monto_from_url = request.GET.get('monto')
        moneda_origen_from_url = request.GET.get('moneda_origen')
        moneda_destino_from_url = request.GET.get('moneda_destino')

        if monto_from_url and moneda_origen_from_url and moneda_destino_from_url:
            initial_data = {
                'monto': monto_from_url,
                'moneda_origen': moneda_origen_from_url,
                'moneda_destino': moneda_destino_from_url,
                # Determinar tipo_operacion basado en las monedas
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

        # Realizar la simulación de cálculo
        resultado_simulacion = calcular_simulacion(
            monto_origen, moneda_origen_codigo, moneda_destino_codigo, user=request.user
        )

        if resultado_simulacion['error']:
            messages.error(request, resultado_simulacion['error'])
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        # --- Validación de Límites (GEG-103) ---
        cliente = request.user.clientes.first() # Asumiendo que un usuario tiene un cliente asociado
        if not cliente:
            messages.error(request, "No se encontró un perfil de cliente asociado a tu usuario.")
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        limite_excedido = False
        limite_mensaje = ""

        # Obtener el límite de transacción (reemplazar con la lógica real de GEG-103)
        limite_transaccion = obtener_limite_transaccion(cliente, moneda_origen_codigo if tipo_operacion == 'compra' else moneda_destino_codigo, tipo_operacion)

        if tipo_operacion == 'compra': # Cliente VENDE divisa extranjera a la casa de cambio (la casa de cambio COMPRA)
            # Validar el monto que el cliente VENDE (monto_origen) contra el límite
            monto_a_validar = monto_origen
            moneda_a_validar = moneda_origen_codigo
        elif tipo_operacion == 'venta': # Cliente COMPRA divisa extranjera de la casa de cambio (la casa de cambio VENDE)
            # Validar el monto que el cliente COMPRA (monto_destino) contra el límite
            monto_a_validar = resultado_simulacion['monto_recibido']
            moneda_a_validar = moneda_destino_codigo

        if monto_a_validar > limite_transaccion:
            limite_excedido = True
            limite_mensaje = f"Has excedido tu límite de transacción de {moneda_a_validar}. Límite: {limite_transaccion} {moneda_a_validar}."

        if limite_excedido:
            messages.error(request, limite_mensaje)
            return render(request, 'core/iniciar_operacion.html', {'form': form})

        # --- Proceder a Confirmación ---
        # Guardar los datos de la operación en la sesión para el paso de confirmación
        request.session['operacion_pendiente'] = {
            'tipo_operacion': tipo_operacion,
            'moneda_origen_codigo': moneda_origen_codigo,
            'monto_origen': str(monto_origen), # Convertir a string para serialización JSON
            'moneda_destino_codigo': moneda_destino_codigo,
            'monto_recibido': str(resultado_simulacion['monto_recibido']),
            'tasa_aplicada': str(resultado_simulacion['tasa_aplicada']),
            'comision_aplicada': str(resultado_simulacion['bonificacion_aplicada']), # bonificacion_aplicada es el descuento de comisión
        }
        return redirect('core:confirmar_operacion')

    return render(request, 'core/iniciar_operacion.html', {'form': form})


@login_required
def confirmar_operacion(request):
    operacion_pendiente = request.session.get('operacion_pendiente')

    if not operacion_pendiente:
        messages.error(request, "No hay una operación pendiente para confirmar.")
        return redirect('core:iniciar_operacion')

    # Convertir montos y tasas de string a Decimal
    operacion_pendiente['monto_origen'] = Decimal(operacion_pendiente['monto_origen'])
    operacion_pendiente['monto_recibido'] = Decimal(operacion_pendiente['monto_recibido'])
    operacion_pendiente['tasa_aplicada'] = Decimal(operacion_pendiente['tasa_aplicada'])
    operacion_pendiente['comision_aplicada'] = Decimal(operacion_pendiente['comision_aplicada'])

    if request.method == 'POST':
        # --- Crear registro de la transacción (GEG-104) ---
        try:
            moneda_origen_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_origen_codigo'])
            moneda_destino_obj = Moneda.objects.get(codigo=operacion_pendiente['moneda_destino_codigo'])
        except Moneda.DoesNotExist:
            messages.error(request, "Error al encontrar las monedas para la transacción.")
            return redirect('core:iniciar_operacion')

        # Determinar el estado inicial según el tipo de operación
        if operacion_pendiente['tipo_operacion'] == 'venta': # Cliente COMPRA divisa extranjera
            estado_inicial = 'pendiente_pago_cliente'
        else: # Cliente VENDE divisa extranjera
            estado_inicial = 'pendiente_deposito_tauser'

        # Generar un código de operación único para el Tauser
        codigo_operacion_tauser = str(uuid.uuid4())[:10]

        transaccion = Transaccion.objects.create(
            cliente=request.user, # El usuario autenticado es el cliente
            tipo_operacion=operacion_pendiente['tipo_operacion'],
            estado=estado_inicial,
            moneda_origen=moneda_origen_obj,
            monto_origen=operacion_pendiente['monto_origen'],
            moneda_destino=moneda_destino_obj,
            monto_destino=operacion_pendiente['monto_recibido'],
            tasa_cambio_aplicada=operacion_pendiente['tasa_aplicada'],
            comision_aplicada=operacion_pendiente['comision_aplicada'],
            codigo_operacion_tauser=codigo_operacion_tauser, # Asignar el código generado
            # Los campos medio_acreditacion_cliente, tauser_utilizado se llenarán en pasos posteriores o se dejarán en null/blank por ahora.
        )
        messages.success(request, f"Operación {transaccion.id} creada con éxito. Estado: {transaccion.get_estado_display()}. Código de operación: {codigo_operacion_tauser}")
        request.session.pop('operacion_pendiente', None) # Limpiar sesión
        return redirect('usuarios:dashboard') # Redirigir al dashboard del usuario o a un historial de transacciones

    return render(request, 'core/confirmar_operacion.html', {'operacion': operacion_pendiente})
