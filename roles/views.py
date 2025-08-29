# roles/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import Role

def is_admin(user):
    """
    Función que comprueba si un usuario es autenticado y de tipo ADMIN.
    """
    return user.is_authenticated and hasattr(user, 'tipo_usuario') and user.tipo_usuario == 'ADMIN'

@user_passes_test(is_admin)
def role_panel(request):
    """
    Renderiza la página para administrar Roles y maneja la creación de nuevos roles.
    """
    # Si el método es POST, significa que se está enviando el formulario para crear un rol.
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre')
        descripcion_rol = request.POST.get('descripcion')
        
        if nombre_rol:
            Role.objects.create(nombre=nombre_rol, descripcion=descripcion_rol)
            messages.success(request, f"Rol '{nombre_rol}' creado exitosamente.")
        else:
            messages.error(request, "El nombre del rol no puede estar vacío.")
        
        return redirect('roles:role-panel') # Redirigimos para evitar reenvío del formulario

    # Si el método es GET, simplemente mostramos la página con la lista de roles.
    roles = Role.objects.all()
    context = {
        'roles': roles
    }
    return render(request, 'roles/role_admin.html', context)

@user_passes_test(is_admin)
def role_delete(request, pk):
    """
    Vista para eliminar un rol específico.
    """
    rol_a_eliminar = get_object_or_404(Role, pk=pk)
    rol_nombre = rol_a_eliminar.nombre
    rol_a_eliminar.delete()
    messages.success(request, f"Rol '{rol_nombre}' eliminado exitosamente.")
    return redirect('roles:role-panel')