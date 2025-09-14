# roles/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Role


@login_required
def role_panel(request):
    """
    Renderiza la página para administrar Roles y maneja la creación de nuevos roles.
    Solo accesible con permiso específico.
    """
    if not request.user.has_perm("roles.access_roles_panel"):
        messages.error(request, "No tienes permiso para acceder a Roles.")
        return redirect("home")

    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre')
        descripcion_rol = request.POST.get('descripcion')
        
        if nombre_rol:
            Role.objects.create(name=nombre_rol, description=descripcion_rol)
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
    if not request.user.has_perm("roles.delete_roles"):
        messages.error(request, "No tienes permiso para eliminar roles.")
        return redirect("home")

    rol_a_eliminar = get_object_or_404(Role, pk=pk)
    rol_nombre = rol_a_eliminar.name   # 👈 cambio aquí
    rol_a_eliminar.delete()
    messages.success(request, f"Rol '{rol_nombre}' eliminado exitosamente.")
    return redirect('roles:role-panel')
