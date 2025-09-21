from django import forms
from .models import MedioAcreditacion

class MedioAcreditacionForm(forms.ModelForm):
    class Meta:
        model = MedioAcreditacion
        exclude = ["moneda", "created_at", "updated_at"]
        widgets = {
            "tipo": forms.Select(),
            "activo": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # UX: agrupar con placeholders y ayudas coherentes a pagos
        self.fields["nombre"].widget.attrs.update({"placeholder": "Ej.: Cuenta Itaú principal"})
        self.fields["entidad_financiera"].widget.attrs.update({"placeholder": "Ej.: Banco Itaú"})
        self.fields["numero_cuenta"].widget.attrs.update({"placeholder": "Ej.: 000-1234567"})
        self.fields["billetera_proveedor"].widget.attrs.update({"placeholder": "Ej.: Tigo Money"})
        self.fields["billetera_alias"].widget.attrs.update({"placeholder": "Ej.: +5959... / alias"})
        self.fields["sucursal_pickup"].widget.attrs.update({"placeholder": "Ej.: Casa Matriz – Asunción"})
