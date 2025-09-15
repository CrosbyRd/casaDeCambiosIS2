from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser

class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name  = forms.CharField(max_length=30, required=True, label="Apellido")
    email      = forms.EmailField(required=True, label="Email")
    password   = forms.CharField(widget=forms.PasswordInput, required=True, label="Contraseña")
    terms      = forms.BooleanField(required=True, label="Acepto términos y privacidad")

    class Meta:
        model  = CustomUser
        fields = ("first_name", "last_name", "email", "password", "terms")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe una cuenta con este email.")
        return email

    def clean_terms(self):
        if not self.cleaned_data.get("terms"):
            raise ValidationError("Debes aceptar los términos y la privacidad.")
        return True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data["email"]  # ya normalizado
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name  = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
        return user


class VerificacionForm(forms.Form):
    codigo = forms.CharField(max_length=6, required=True, label="Código de verificación")
