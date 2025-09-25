from django import forms
from .models import TransactionLimit

class TransactionLimitForm(forms.ModelForm):
    class Meta:
        model = TransactionLimit
        fields = ['aplica_diario', 'monto_diario', 'aplica_mensual', 'monto_mensual']
        widgets = {
            'monto_diario': forms.NumberInput(attrs={'placeholder': 'Monto Diario PYG'}),
            'monto_mensual': forms.NumberInput(attrs={'placeholder': 'Monto Mensual PYG'}),
        }
