# core/forms.py
from django import forms
from monedas.models import Moneda
from transacciones.models import Transaccion
from pagos.models import TipoMedioPago, MedioPagoCliente
from medios_acreditacion.models import TipoMedioAcreditacion, MedioAcreditacionCliente

class SimulacionForm(forms.Form):
    monto = forms.DecimalField(
        label="Monto a cambiar",
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1.000.000'})
    )
    moneda_origen = forms.ChoiceField(
        label="Moneda que tengo",
        widget=forms.Select(attrs={'class': ''})
    )
    moneda_destino = forms.ChoiceField(
        label="Moneda que quiero",
        widget=forms.Select(attrs={'class': ''})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Actualiza las opciones cada vez que se instancia el formulario
        # para reflejar cualquier cambio en la base de datos sin reiniciar el servidor.
        try:
            monedas = Moneda.objects.all()
            choices = [(m.codigo, m.nombre) for m in monedas]
        except Exception:
            choices = [('PYG', 'Guaraní')]

        self.fields['moneda_origen'].choices = choices
        self.fields['moneda_destino'].choices = choices # Añadido para corregir el problema
    def clean_monto(self):
        monto = self.cleaned_data['monto']
        moneda_origen_codigo = self.cleaned_data.get('moneda_origen')

        if moneda_origen_codigo:
            try:
                moneda_origen_obj = Moneda.objects.get(codigo=moneda_origen_codigo)
                if monto < moneda_origen_obj.minima_denominacion:
                    raise forms.ValidationError(
                        f"El monto mínimo para cambiar {moneda_origen_obj.nombre} es {moneda_origen_obj.minima_denominacion}."
                    )
            except Moneda.DoesNotExist:
                # Esto debería ser manejado por la validación de ChoiceField, pero es un fallback
                pass
        return monto

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get("moneda_origen")
        destino = cleaned_data.get("moneda_destino")

        if origen and destino:
            if origen == destino:
                raise forms.ValidationError("Las monedas no pueden ser iguales.")
            if origen != 'PYG' and destino != 'PYG':
                raise forms.ValidationError("La simulación debe involucrar Guaraníes (PYG).")
        return cleaned_data

class OperacionForm(SimulacionForm):
    tipo_operacion = forms.ChoiceField(
        label="Tipo de Operación",
        choices=Transaccion.TIPO_OPERACION_CHOICES,
        widget=forms.Select(attrs={'class': ''})
    )
    medio_pago = forms.ModelChoiceField(
        label="Mi Medio de Pago",
        queryset=MedioPagoCliente.objects.none(), # Se inicializará en __init__
        widget=forms.Select(attrs={'class': ''}),
        required=False, # No es requerido para todas las operaciones (ej. compra de la casa de cambio)
    )
    medio_acreditacion = forms.ChoiceField(
        label="Mi Medio de Acreditación (Dónde recibiré mi dinero)",
        choices=[], # Se inicializará en __init__
        widget=forms.Select(attrs={'class': ''}),
        required=False, # No es requerido para todas las operaciones (ej. venta de la casa de cambio)
    )
    
    # --- NUEVO CAMPO AÑADIDO ---
    METODOS_ENTREGA_CHOICES = [
        ('efectivo', 'Depositar Dólares en Tauser (Efectivo)'),
        ('stripe', 'Pagar Dólares con Tarjeta (Stripe)'),
    ]
    metodo_entrega = forms.ChoiceField(
        choices=METODOS_ENTREGA_CHOICES,
        label="¿Cómo nos entregarás los dólares?",
        widget=forms.RadioSelect, # Usamos RadioSelect para mejor UX
        required=False,  # Muy importante, ya que solo aplica a un caso
        initial='efectivo'
    )
    # ---------------------------

    modalidad_tasa = forms.ChoiceField(
        label="Modalidad de Tasa",
        choices=Transaccion.MODALIDAD_TASA_CHOICES,
        widget=forms.Select(attrs={'class': ''}),
        initial='bloqueada', # Por defecto, la tasa bloqueada
        help_text="Elige si la tasa se bloquea por un tiempo o es indicativa."
    )

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop('cliente', None) # Obtener el cliente
        super().__init__(*args, **kwargs) # Llama al __init__ de SimulacionForm para cargar las monedas
        if self.cliente:
            self.fields['medio_pago'].queryset = MedioPagoCliente.objects.filter(
                cliente=self.cliente, activo=True
            ).select_related('tipo') # Optimizar consulta

            # Configurar opciones para medio_acreditacion (sin 'Efectivo' hardcodeado)
            acreditacion_choices = []
            medios_acreditacion_cliente = MedioAcreditacionCliente.objects.filter(
                cliente=self.cliente, activo=True
            ).select_related('tipo')
            acreditacion_choices.extend([(str(m.id_medio), f"{m.alias} ({m.tipo.nombre})") for m in medios_acreditacion_cliente])
            self.fields['medio_acreditacion'].choices = acreditacion_choices
            # Si no hay medios de acreditación, el campo debería ser requerido y el usuario redirigido a crear uno.
            # Esto ya se maneja en core/views.py

    def clean(self):
        cleaned_data = super().clean()
        tipo_operacion = cleaned_data.get("tipo_operacion")
        moneda_origen = cleaned_data.get("moneda_origen")
        moneda_destino = cleaned_data.get("moneda_destino")
        medio_pago = cleaned_data.get("medio_pago")
        medio_acreditacion = cleaned_data.get("medio_acreditacion")

        if tipo_operacion and moneda_origen and moneda_destino:
            if tipo_operacion == 'compra': # Cliente VENDE divisa extranjera a la casa de cambio
                if moneda_origen == 'PYG':
                    raise forms.ValidationError("Para 'Compra de Divisa', la moneda de origen no puede ser PYG.")
                if moneda_destino != 'PYG':
                    raise forms.ValidationError("Para 'Compra de Divisa', la moneda de destino debe ser PYG.")
                # Si es una compra (cliente recibe dinero), el medio de acreditación SIEMPRE es obligatorio.
                if not medio_acreditacion:
                    self.add_error('medio_acreditacion', 'Debe seleccionar un medio de acreditación para recibir su dinero.')

            elif tipo_operacion == 'venta': # Cliente COMPRA divisa extranjera de la casa de cambio
                if moneda_origen != 'PYG':
                    raise forms.ValidationError("Para 'Venta de Divisa', la moneda de origen debe ser PYG.")
                if moneda_destino == 'PYG':
                    raise forms.ValidationError("Para 'Venta de Divisa', la moneda de destino no puede ser PYG.")
                # Si es una venta (cliente paga), el medio de pago es obligatorio
                if not medio_pago:
                    self.add_error('medio_pago', 'Debe seleccionar un medio de pago para esta operación.')

        return cleaned_data
