# ted/forms.py
from django import forms
from monedas.models import TedMovimiento
"""
Formularios para la gestión de ajustes de inventario del Tauser.

Este módulo define los formularios utilizados para registrar ajustes de billetes
en el inventario del Tauser (TedInventario). Permite especificar la cantidad a
sumar o restar, el motivo del ajuste, un comentario opcional y la confirmación
del usuario.

Clases:
    AjusteInventarioForm: Formulario principal para registrar un ajuste de inventario.

"""
class AjusteInventarioForm(forms.Form):
    """
    Formulario para registrar ajustes manuales en el inventario de billetes.

    Campos:
        delta (IntegerField): Cantidad de billetes a ajustar. Valores positivos suman,
            valores negativos restan.
        motivo (ChoiceField): Motivo del ajuste. Puede ser un ajuste manual o 'otro'.
        comentario (CharField): Comentario opcional sobre el ajuste (máx. 140 caracteres).
        confirm (BooleanField): Confirmación obligatoria por parte del usuario para validar el ajuste.
    """
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
