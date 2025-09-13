# core/forms.py
from django import forms
from monedas.models import Moneda

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
        self.fields['moneda_destino'].choices = choices

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
