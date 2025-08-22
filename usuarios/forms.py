from django import forms
from .models import CustomUser

# usuarios/forms.py
from django import forms
from .models import CustomUser
from django.contrib.auth.forms import UserCreationForm

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'password')  # Solo los que usas en el template


class VerificacionForm(forms.Form):
    codigo = forms.CharField(max_length=6, required=True, label="Código de verificación")
