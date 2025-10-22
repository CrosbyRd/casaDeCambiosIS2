from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from functools import wraps

class AdminRequiredMixin(AccessMixin):
    """
    Mixin que asegura que el usuario autenticado tiene el rol de 'Administrador'.
    Si no está autenticado, lo redirige a la página de login.
    Si está autenticado pero no tiene el rol de 'Administrador', lo redirige a la página de inicio.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Asumiendo que el modelo CustomUser tiene una relación ManyToMany con Role
        # y que el nombre del rol de administrador es 'Administrador'.
        if not request.user.roles.filter(name='Administrador').exists():
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect(reverse_lazy('home')) # Redirige a la página de inicio
        
        return super().dispatch(request, *args, **kwargs)

def admin_required(func):
    """
    Decorador para funciones de vista que requieren el rol de 'Administrador'.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Debes iniciar sesión para acceder a esta sección.")
            return redirect(reverse_lazy('login')) # Asumiendo que tienes una URL 'login'
        
        if not request.user.roles.filter(name='Administrador').exists():
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect(reverse_lazy('home')) # Redirige a la página de inicio
        
        return func(request, *args, **kwargs)
    return wrapper
