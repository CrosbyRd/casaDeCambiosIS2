from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer
from .models import CustomUser

# Vista para el registro de usuarios
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (permissions.AllowAny,) # Cualquiera puede registrarse
    serializer_class = RegisterSerializer


# Vista para obtener los datos del usuario logueado
class CurrentUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,) # Solo usuarios autenticados

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
# Vista para listar y crear usuarios.
# Solo los administradores podrán acceder a esta vista.
class UserListCreate(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# Vista para recuperar, actualizar y eliminar un usuario específico.
# Solo los administradores podrán acceder a esta vista.
class UserRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]