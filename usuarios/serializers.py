# usuarios/serializers.py
from rest_framework import serializers
from .models import CustomUser
from roles.serializers import RoleSerializer # Asegúrate de que este import exista
from roles.models import Role # Importa el modelo Role

class UserSerializer(serializers.ModelSerializer):
    """
    Serializador para mostrar la información del usuario (sin datos sensibles).
    Incluye la información de los roles asignados.
    """
    roles = RoleSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'roles']


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro de nuevos usuarios.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        # Asignamos el rol 'CLIENTE' por defecto a los nuevos usuarios registrados
        try:
            client_role = Role.objects.get(name='CLIENTE')
            user.roles.add(client_role)
        except Role.DoesNotExist:
            pass
        
        return user