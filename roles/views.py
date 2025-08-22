from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
# Create your views here.
from rest_framework import generics, permissions
from .models import Role
from .serializers import RoleSerializer



class RoleListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear Roles.
    Solo los administradores pueden acceder.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]

class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar y eliminar un Rol específico.
    Solo los administradores pueden acceder.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


def is_admin(user):
    return user.is_authenticated and user.tipo_usuario == 'ADMIN'


@user_passes_test(is_admin)
def role_panel(request):
    """
    Renderiza la página HTML para administrar Roles.
    Solo accesible a administradores.
    """
    return render(request, 'roles/role_admin.html')