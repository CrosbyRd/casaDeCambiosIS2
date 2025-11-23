# roles/views.py
"""
Módulo de vistas para la aplicación **Roles**.

Contiene las vistas para la gestión de roles de usuarios,
incluyendo:
    - Panel de administración de roles.
    - Asignación de roles a usuarios específicos.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Role
from usuarios.models import CustomUser


@login_required
def role_panel(request):
    """
    Renderiza el panel de administración de roles.

    Solo accesible si el usuario tiene el permiso `roles.access_roles_panel`.

    Returns
    -------
    HttpResponse
        Página con listado de usuarios y sus roles.
    """
    if not request.user.has_perm("roles.access_roles_panel"):
        return redirect("home")

    usuarios = CustomUser.objects.all().order_by('first_name', 'last_name')
    context = {
        'usuarios': usuarios
    }
    return render(request, 'roles/role_admin.html', context)


@login_required
def manage_user_roles(request, user_id):
    """
    Gestiona la asignación de roles a un usuario específico.

    Permiso requerido: `usuarios.access_user_client_management`.

    Parameters
    ----------
    request : HttpRequest
        Objeto de solicitud HTTP.
    user_id : int
        ID del usuario al que se le asignarán roles.

    Returns
    -------
    HttpResponse
        Redirecciona al panel de roles o renderiza formulario de gestión.
    """
    if not request.user.has_perm("usuarios.access_user_client_management"):
        return redirect("home")

    user_to_manage = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        # Obtener los IDs de los roles seleccionados en el formulario
        selected_role_ids = request.POST.getlist('roles')
        
        # Limpiar los roles actuales y asignar los nuevos
        user_to_manage.roles.clear()
        for role_id in selected_role_ids:
            role = Role.objects.get(id=role_id)
            user_to_manage.roles.add(role)
        
        messages.success(request, f"Roles para {user_to_manage.email} actualizados correctamente.")
        return redirect("roles:role-panel")

    # Para el método GET, mostrar el formulario
    all_roles = Role.objects.all()
    user_roles = user_to_manage.roles.all()
    
    context = {
        'user_to_manage': user_to_manage,
        'all_roles': all_roles,
        'user_roles': user_roles
    }
    return render(request, 'roles/manage_user_roles.html', context)
