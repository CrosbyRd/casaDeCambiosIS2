"""Formularios de la aplicación *pagos*.

Incluye formularios basados en modelos para crear y editar instancias
de :class:`pagos.models.TipoMedioPago`.
"""
from django import forms
from .models import TipoMedioPago


class TipoMedioPagoForm(forms.ModelForm):
    """Formulario para crear/editar :class:`pagos.models.TipoMedioPago`.

    Contiene validaciones implícitas según los ``validators`` definidos en el
    modelo (rango de 0–100 para comisión y bonificación) y expone el campo
    ``activo`` para habilitar/deshabilitar el medio de pago.

    .. tip::
       Los ``help_text`` definidos en el modelo se muestran automáticamente
       en las vistas basadas en este formulario.

    """

    class Meta:
        model = TipoMedioPago
        fields = [
            "nombre",
            "comision_porcentaje",
            "bonificacion_porcentaje",
            "activo",
        ]
        # Los labels/helps se heredan desde el modelo.
