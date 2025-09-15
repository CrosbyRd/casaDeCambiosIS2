"""Admin Panel — modelos
=======================

Modelos mínimos para declarar permisos a nivel de aplicación del panel de
administración propio. No crea tablas en la base de datos: únicamente
registra *Django permissions* mediante ``Meta.permissions``.

.. note::
   Este módulo no define tablas reales; se usa únicamente para registrar
   permisos personalizados en el sistema de autenticación de Django.

"""

from django.db import models


class AdminPanelPermissions(models.Model):
    """Contenedor “virtual” de permisos del Admin Panel.

    Esta clase **no** se persiste (``managed = False``) y solo existe para
    declarar permisos a través de :class:`~django.db.models.Options.permissions`.

    **Permisos registrados**

    * ``admin_panel.access_admin_dashboard`` — *Puede acceder al dashboard del Admin Panel*.

    .. important::
       Al tener ``managed = False`` no habrá migraciones para esta clase.
       Aun así, el permiso queda disponible en la tabla de *auth* porque
       Django lee la opción ``Meta.permissions`` y lo registra.

    """

    class Meta:
        #: Evita que Django cree/gestione una tabla para este modelo.
        managed = False
        #: Desactiva permisos por defecto (add/change/delete/view).
        default_permissions = ()
        #: Declaración explícita de permisos del app.
        permissions = [
            (
                "access_admin_dashboard",
                "Puede acceder al dashboard del Admin Panel",
            ),
        ]
