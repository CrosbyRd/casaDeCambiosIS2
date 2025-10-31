"""
Serializadores para la aplicación **Roles**.

Incluye:
    - RoleSerializer: serializa roles y sus permisos para APIs REST.
"""
from rest_framework import serializers
from .models import Role

class RoleSerializer(serializers.ModelSerializer):
    """
    Serializador de roles para APIs REST.

    Permite listar y obtener detalles de un rol incluyendo sus permisos.

    Attributes
    ----------
    id : int
        Identificador del rol.
    name : str
        Nombre del rol.
    description : str
        Descripción opcional.
    permissions : list
        Lista de permisos asociados.
    """
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions']