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
    Regla flexible para considerar a un usuario como 'admin':
    - is_superuser o is_staff
    - o pertenece a roles ManyToMany con name=ADMIN_ROLE_NAME
    - o pertenece a grupos de Django con name=ADMIN_ROLE_NAME
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
    """Redirige a 'home' si existe, si no a raíz '/'."""
    try:
        return redirect(reverse("home"))
    except NoReverseMatch:
        return redirect("/")


class AdminRequiredMixin(AccessMixin):
    """
    Mixin que asegura que el usuario autenticado tenga privilegios de administrador.
    - Si no está autenticado: usa la mecánica de AccessMixin (LOGIN_URL).
    - Si está autenticado pero sin permisos: mensaje y redirección a 'home' (o '/').
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
    Decorador para vistas de función que requieren privilegios de administrador.
    Acepta las mismas reglas que AdminRequiredMixin.
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
