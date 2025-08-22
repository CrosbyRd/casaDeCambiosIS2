from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer
from .models import CustomUser
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

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

class AdminPanelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Validamos que sea ADMIN
        if request.user.tipo_usuario != 'ADMIN':
            return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
        # Renderizamos el HTML
        return render(request, 'usuarios/admin_panel.html')