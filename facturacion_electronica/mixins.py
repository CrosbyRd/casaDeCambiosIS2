"""
Mixins y Decoradores de la app Facturación Electrónica.

.. module:: facturacion_electronica.mixins
   :synopsis: Mixins y decoradores para control de acceso en el módulo de Facturación Electrónica.

Este módulo proporciona mixins y decoradores para asegurar que solo los usuarios
con privilegios de administrador puedan acceder a ciertas vistas y funcionalidades.
"""
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy, NoReverseMatch


# Nombre del rol/grupo administrador configurable (opcional)
ADMIN_ROLE_NAME = getattr(settings, "FACTURACION_ELECTRONICA_ADMIN_ROLE_NAME", "Administrador")


def _user_is_admin(user) -> bool:
    """
    Verifica si un usuario tiene privilegios de administrador.

    Un usuario se considera administrador si:
    - Está autenticado.
    - Es superusuario o miembro del staff.
    - O pertenece a un rol (si el modelo de usuario tiene una relación 'roles')
      o a un grupo de Django con el nombre definido en `ADMIN_ROLE_NAME`.

    :param user: El objeto de usuario a verificar.
    :type user: django.contrib.auth.models.User o CustomUser
    :return: True si el usuario es administrador, False en caso contrario.
    :rtype: bool
    """
    if not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    # Soporte opcional para relación roles (ManyToMany) si existe en tu CustomUser
    if hasattr(user, "roles"):
        try:
            if user.roles.filter(name=ADMIN_ROLE_NAME).exists():
                return True
        except Exception:
            # Si la relación existe pero falla el query, continúa con otras comprobaciones
            pass

    # Fallback a grupos nativos de Django
    if hasattr(user, "groups"):
        try:
            if user.groups.filter(name=ADMIN_ROLE_NAME).exists():
                return True
        except Exception:
            pass

    return False


def _redirect_home():
    """
    Redirige al usuario a la página de inicio ('home') o a la raíz del sitio ('/')
    si la URL 'home' no está definida.

    :return: Un objeto HttpResponseRedirect para la redirección.
    :rtype: django.http.HttpResponseRedirect
    """
    try:
        return redirect(reverse("home"))
    except NoReverseMatch:
        return redirect("/")


class AdminRequiredMixin(AccessMixin):
    """
    Mixin para vistas basadas en clases que requiere que el usuario autenticado
    tenga privilegios de administrador.

    - Si el usuario no está autenticado, se le redirige a la página de login
      (según la configuración de `LOGIN_URL` de Django).
    - Si el usuario está autenticado pero no tiene permisos de administrador,
      se muestra un mensaje de error y se le redirige a la página de inicio.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not _user_is_admin(request.user):
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return _redirect_home()

        return super().dispatch(request, *args, **kwargs)


def admin_required(func):
    """
    Decorador para vistas basadas en funciones que requieren privilegios de administrador.

    Aplica las mismas reglas de verificación de permisos que :class:`AdminRequiredMixin`.
    - Si el usuario no está autenticado, se le redirige a la página de login.
    - Si el usuario está autenticado pero no tiene permisos de administrador,
      se muestra un mensaje de error y se le redirige a la página de inicio.

    :param func: La función de vista a decorar.
    :type func: callable
    :return: La función de vista decorada.
    :rtype: callable
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            messages.error(request, "Debes iniciar sesión para acceder a esta sección.")
            # Usamos reverse_lazy('login') si existe, si no fallback a settings.LOGIN_URL o '/accounts/login/'
            login_url = None
            try:
                login_url = reverse_lazy("login")
            except NoReverseMatch:
                login_url = getattr(settings, "LOGIN_URL", "/accounts/login/")
            return redirect(login_url)

        if not _user_is_admin(request.user):
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return _redirect_home()

        return func(request, *args, **kwargs)
    return wrapper
