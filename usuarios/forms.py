from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser


class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", max_length=30, required=True)
    last_name = forms.CharField(label="Apellido", max_length=30, required=True)
    email = forms.EmailField(label="Email", required=True)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=True)
    terms = forms.BooleanField(label="Acepto términos y privacidad", required=True)

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "password")  # terms no se guarda en DB

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe un usuario con este email.")
        return email

    def clean_first_name(self):
        return (self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self):
        return (self.cleaned_data.get("last_name") or "").strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        # email ya viene normalizado en clean_email
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user


class VerificacionForm(forms.Form):
    codigo = forms.CharField(max_length=6, required=True, label="Código de verificación")
