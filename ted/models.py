from django.db import models

class TedPerms(models.Model):
    """
    Modelo mínimo para declarar permisos de la app TED.
    No se usa en lógica; solo existe para registrar el permiso custom.
    """
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("puede_operar_terminal", "Puede operar el terminal TED"),
        ]
