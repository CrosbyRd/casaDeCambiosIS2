from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    # Campos de solo lectura para mostrar información calculada
    bonificacion_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly', 
            'class': 'form-control',
            'id': 'id_bonificacion_display'
        }),
        label='Bonificación (%)'
    )
    
    limite_usd_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'form-control',
            'id': 'id_limite_usd_display'
        }),
        label='Límite USD'
    )
    
    class Meta:
        model = Cliente
        fields = ['nombre', 'categoria', 'activo']   # 🔹 Quitamos correo_electronico
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={
                'class': 'form-select', 
                'id': 'id_categoria',
                'onchange': 'actualizarInformacionCliente(this)'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'activo': 'Cliente activo',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer valores iniciales basados en la categoría
        if self.instance and self.instance.pk:
            self.fields['bonificacion_display'].initial = f"{self.instance.bonificacion}%"
            self.fields['limite_usd_display'].initial = f"${self.instance.limite_compra_usd:,.2f}"
        else:
            # Valores por defecto para nuevo cliente (Minorista)
            self.fields['bonificacion_display'].initial = "0%"
            self.fields['limite_usd_display'].initial = "$5,000.00"


class ClienteSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Buscar',
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar por nombre...',
            'class': 'form-control'
        })
    )
    
    categoria = forms.ChoiceField(
        required=False,
        choices=[('', 'Todas las categorías')] + list(Cliente.Categoria.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    activo = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
