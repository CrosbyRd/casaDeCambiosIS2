# notificaciones/models.py
"""
Módulo de modelos para la aplicación de notificaciones.

Define las entidades relacionadas con la configuración de preferencias de notificación
de los usuarios y las notificaciones individuales que el sistema genera y envía.

:author: Equipo de desarrollo Global Exchange
:since: 2025-10-16
"""
import uuid
from django.db import models
from django.conf import settings
from monedas.models import Moneda

class PreferenciasNotificacion(models.Model):
    """
    Modelo que almacena las **preferencias de notificación** asociadas a un usuario.

    Permite definir si el usuario desea recibir notificaciones por correo electrónico
    cuando cambian las tasas de cambio y qué monedas desea seguir.

    :cvar usuario: Relación uno a uno con el usuario propietario de las preferencias.
    :type usuario: django.db.models.OneToOneField

    :cvar recibir_email_tasa_cambio: Indica si el usuario desea recibir correos cuando
        se actualizan las tasas de cambio.
    :type recibir_email_tasa_cambio: bool

    :cvar monedas_seguidas: Conjunto de monedas que el usuario desea seguir para
        recibir notificaciones.
    :type monedas_seguidas: django.db.models.ManyToManyField

    :ivar id: Identificador primario (automático).
    :ivar usuario: Usuario vinculado a las preferencias.
    :ivar recibir_email_tasa_cambio: Preferencia sobre el canal de notificación.
    :ivar monedas_seguidas: Lista de monedas seguidas por el usuario.
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
    Modelo que representa una **notificación individual** generada por el sistema.

    Cada notificación está asociada a un usuario destinatario, contiene un mensaje,
    una marca de lectura y puede estar silenciada si el usuario no desea verla
    en el tablón principal.

    :cvar id: Identificador único de la notificación (UUID).
    :type id: uuid.UUID
    :cvar destinatario: Usuario que recibe la notificación.
    :type destinatario: django.db.models.ForeignKey
    :cvar mensaje: Texto con el contenido de la notificación.
    :type mensaje: str
    :cvar leida: Indica si la notificación ya fue leída por el usuario.
    :type leida: bool
    :cvar silenciada: Indica si la notificación está silenciada (oculta en el tablón).
    :type silenciada: bool
    :cvar fecha_creacion: Fecha y hora en que se generó la notificación.
    :type fecha_creacion: datetime
    :cvar url_destino: Enlace opcional que permite al usuario navegar al origen
        de la notificación.
    :type url_destino: str | None
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
        """
        Metadatos del modelo.

        :cvar ordering: Orden de las notificaciones (más recientes primero).
        :type ordering: list[str]
        :cvar verbose_name: Nombre legible en singular.
        :type verbose_name: str
        :cvar verbose_name_plural: Nombre legible en plural.
        :type verbose_name_plural: str
        """
        ordering = ['-fecha_creacion']
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
