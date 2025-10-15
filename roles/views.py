# roles/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Role
from usuarios.models import CustomUser


@login_required
def role_panel(request):
    """
    Renderiza la página para administrar Roles de usuarios.
    Solo accesible con permiso específico.
    """
    if not request.user.has_perm("roles.access_roles_panel"):
        messages.error(request, "No tienes permiso para acceder a la gestión de roles de usuarios.")
        return redirect("home")

    usuarios = CustomUser.objects.all().order_by('first_name', 'last_name')
    context = {
        'usuarios': usuarios
    }
    return render(request, 'roles/role_admin.html', context)


@login_required
def manage_user_roles(request, user_id):
    """
    Asigna o desasigna roles a un usuario específico.
    """
    if not request.user.has_perm("usuarios.access_user_client_management"):
        messages.error(request, "No tienes permiso para gestionar roles de usuarios.")
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
        return redirect('usuarios:listar_usuarios')

    # Para el método GET, mostrar el formulario
    all_roles = Role.objects.all()
    user_roles = user_to_manage.roles.all()
    
    context = {
        'user_to_manage': user_to_manage,
        'all_roles': all_roles,
        'user_roles': user_roles
    }
    return render(request, 'roles/manage_user_roles.html', context)
