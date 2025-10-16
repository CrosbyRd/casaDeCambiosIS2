# notificaciones/models.py

import uuid
from django.db import models
from django.conf import settings
from monedas.models import Moneda

class PreferenciasNotificacion(models.Model):
    """
    Almacena las preferencias de notificación para un usuario.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferencias_notificacion'
    )
    # Preferencias de canal
    recibir_email_tasa_cambio = models.BooleanField(
        default=True,
        help_text="Recibir notificaciones por correo cuando una tasa de interés cambia."
    )
    # Preferencias de contenido
    monedas_seguidas = models.ManyToManyField(
        Moneda,
        blank=True,
        related_name='seguidores',
        help_text="El usuario recibirá notificaciones sobre estas monedas."
    )

    def __str__(self):
        return f"Preferencias de {self.usuario.email}"

    class Meta:
        verbose_name = "Preferencias de Notificación"
        verbose_name_plural = "Preferencias de Notificaciones"

class Notificacion(models.Model):
    """
    Representa una notificación individual para un usuario.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    silenciada = models.BooleanField(default=False, help_text="Si es True, no se muestra en el tablón principal.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Opcional: para poder hacer click y navegar a un lugar relevante
    url_destino = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Notificación para {self.destinatario.email}: {self.mensaje[:30]}..."

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
