"""
Formularios de la aplicación **configuracion**.

.. module:: configuracion.forms
   :synopsis: Formularios para administrar los límites transaccionales.

Incluye el formulario para crear y editar instancias de :class:`TransactionLimit`,
con widgets personalizados y validaciones por defecto de Django.
"""
from django import forms
from .models import TransactionLimit

class TransactionLimitForm(forms.ModelForm):
    """
    Formulario para crear o editar un límite de transacción.

    
    Formulario para crear o editar un límite de transacción.

    **Campos incluidos**
    -------------------
    aplica_diario : BooleanField
        Indica si aplica límite diario.
    monto_diario : IntegerField  <-- ACTUALIZAR ESTO (era DecimalField)
        Monto máximo permitido diario, con placeholder "Monto Diario PYG".
    aplica_mensual : BooleanField
        Indica si aplica límite mensual.
    monto_mensual : IntegerField  <-- ACTUALIZAR ESTO (era DecimalField)
        Monto máximo permitido mensual, con placeholder "Monto Mensual PYG".

    **Widgets**
    -----------
    - monto_diario: NumberInput con placeholder.
    - monto_mensual: NumberInput con placeholder.
    """
    class Meta:
        model = TransactionLimit
        fields = ['aplica_diario', 'monto_diario', 'aplica_mensual', 'monto_mensual']
        widgets = {
            'monto_diario': forms.NumberInput(attrs={'placeholder': 'Monto Diario PYG'}),
            'monto_mensual': forms.NumberInput(attrs={'placeholder': 'Monto Mensual PYG'}),
        }
