from rest_framework import serializers
from .models import CustomUser
from roles.models import Role

class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer para mostrar la información de un Rol.
    """
    class Meta:
        model = Role
        fields = ['name']

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para mostrar la información del usuario (sin datos sensibles).
    """
    roles = RoleSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        # CORREGIDO: Solo usamos campos que existen en el modelo CustomUser.
        fields = ['id', 'email', 'first_name', 'last_name', 'roles']


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro de nuevos usuarios.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        # CORREGIDO: Solo usamos campos que existen en el modelo CustomUser.
        fields = ['password', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        try:
            default_role, _ = Role.objects.get_or_create(name='CLIENTE')
            user.roles.add(default_role)
        except Exception as e:
            print(f"No se pudo asignar el rol por defecto: {e}")
            
        return user