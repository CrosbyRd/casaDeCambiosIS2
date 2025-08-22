# MERGE: Imports de ambas ramas, organizados y sin duplicados
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer
from .forms import RegistroForm, VerificacionForm
from clientes.models import Cliente

# --- Vistas de Autoregistro y Verificación (Tu rama - HEAD) ---


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    data = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_verified": user.is_verified,
    }
    return Response(data)



def register(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # El usuario no está activo hasta que se verifique
            user.password = make_password(form.cleaned_data['password'])
            user.save() # Guardamos primero para tener un ID
            
            user.generate_verification_code()
      
            send_mail(
                "Código de verificación",
                f"Tu código de verificación es: {user.verification_code}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # Usamos el email para la verificación para no depender del ID
            request.session['email_verificacion'] = user.email
            return redirect('usuarios:verify')
        else:
            return render(request, "site/signup.html", {"form": form})
    else:
        form = RegistroForm()
    return render(request, "site/signup.html", {"form": form})

def verify(request):
    email = request.session.get('email_verificacion')
    if not email:
        messages.error(request, "Sesión de verificación inválida. Por favor, regístrate de nuevo.")
        return redirect('usuarios:register')

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, "El usuario no existe.")
        return redirect('usuarios:register')
        
    form = VerificacionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        codigo = form.cleaned_data['codigo']
        if user.is_code_valid(codigo, minutes_valid=5): # Damos 5 minutos de validez
            user.is_active = True
            user.is_verified = True
            user.verification_code = None
            user.code_created_at = None
            user.save()
            request.session.pop('email_verificacion', None)
            messages.success(request, "¡Cuenta verificada correctamente! Ya puedes iniciar sesión.")
            return redirect('site_login') # Asumiendo que tienes una URL con este nombre
        else:
            messages.error(request, "Código incorrecto o expirado.")
            
    return render(request, "site/verify.html", {"form": form, "email": user.email})

def reenviar_codigo(request):
    email = request.session.get('email_verificacion')
    if not email:
        messages.error(request, "No hay una sesión de verificación activa.")
        return redirect('usuarios:register')

    user = get_object_or_404(CustomUser, email=email)
    user.generate_verification_code()
    
    send_mail(
        "Nuevo código de verificación",
        f"Tu nuevo código de verificación es: {user.verification_code}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    messages.success(request, f"Se ha enviado un nuevo código a {user.email}.")
    return redirect('usuarios:verify')

# --- Vistas de API (Rama entrante) ---

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class CurrentUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class UserListCreate(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class UserRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

# --- Vistas de Administración (Rama entrante) ---

def admin_panel(request):
    return render(request, 'usuarios/admin_panel.html')

def listar_usuarios(request):
    usuarios = CustomUser.objects.all().prefetch_related('clientes', 'roles')
    todos_clientes = Cliente.objects.all()
    return render(request, 'usuarios/listar_usuarios.html', {
        'usuarios': usuarios,
        'todos_clientes': todos_clientes
    })

def agregar_cliente(request, user_id, cliente_id):
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.add(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' agregado a {user.email}.")
    return redirect('usuarios:listar_usuarios')

def quitar_cliente(request, user_id, cliente_id):
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.remove(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' quitado de {user.email}.")
    return redirect('usuarios:listar_usuarios')