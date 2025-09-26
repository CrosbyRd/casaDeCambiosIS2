# ted/forms.py
from django import forms
from monedas.models import TedMovimiento

class AjusteInventarioForm(forms.Form):
    delta = forms.IntegerField(
        label="Ajuste (+ suma, − resta)",
        help_text="Usa valores positivos para ingresar billetes y negativos para retirarlos.",
    )
    motivo = forms.ChoiceField(
        label="Motivo",
        choices=[
            (TedMovimiento.MOTIVO_AJUSTE, "Ajuste manual"),
            (TedMovimiento.MOTIVO_OTRO, "Otro"),
        ],
        initial=TedMovimiento.MOTIVO_AJUSTE,
    )
    comentario = forms.CharField(
        label="Comentario (opcional)",
        required=False,
        max_length=140,
    )
    confirm = forms.BooleanField(
        label="Confirmo el ajuste",
        required=True,
    )
