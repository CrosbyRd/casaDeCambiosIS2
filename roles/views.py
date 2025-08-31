# roles/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Role


# --- Función auxiliar para verificar si es admin ---
def es_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
def role_panel(request):
    """
    Renderiza la página para administrar Roles y maneja la creación de nuevos roles.
    Solo accesible para usuarios autenticados y staff.
    """
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")

    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre')
        descripcion_rol = request.POST.get('descripcion')
        
        if nombre_rol:
            Role.objects.create(nombre=nombre_rol, descripcion=descripcion_rol)
            messages.success(request, f"Rol '{nombre_rol}' creado exitosamente.")
        else:
            messages.error(request, "El nombre del rol no puede estar vacío.")
        
        return redirect('roles:role-panel')  # Redirigimos para evitar reenvío del formulario

    roles = Role.objects.all()
    context = {
        'roles': roles
    }
    return render(request, 'roles/role_admin.html', context)


@login_required
def role_delete(request, pk):
    """
    Vista para eliminar un rol específico.
    Solo accesible para usuarios autenticados y staff.
    """
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")

    rol_a_eliminar = get_object_or_404(Role, pk=pk)
    rol_nombre = rol_a_eliminar.nombre
    rol_a_eliminar.delete()
    messages.success(request, f"Rol '{rol_nombre}' eliminado exitosamente.")
    return redirect('roles:role-panel')
