# roles/views.py
from django.shortcuts import render
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