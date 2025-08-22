from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer
from .models import CustomUser
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from clientes.models import Cliente



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

def admin_panel(request):
        return render(request, 'usuarios/admin_panel.html')
    


def listar_usuarios(request):
    usuarios = CustomUser.objects.all().prefetch_related('clientes')
    todos_clientes = Cliente.objects.all()
    return render(request, 'usuarios/listar_usuarios.html', {
        'usuarios': usuarios,
        'todos_clientes': todos_clientes
    })

def agregar_cliente(request, user_id, cliente_id):
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.add(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' agregado a {user.username}.")
    return redirect('usuarios:listar_usuarios')

def quitar_cliente(request, user_id, cliente_id):
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.remove(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' quitado de {user.username}.")
    return redirect('usuarios:listar_usuarios')