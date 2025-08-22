from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer
from .models import CustomUser
from django.shortcuts import render
from django.utils import timezone

# usuarios/views.py
from django.shortcuts import render, redirect
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMessage
from django.contrib import messages
from django.conf import settings
from datetime import datetime, timedelta
from .forms import RegistroForm, VerificacionForm
import random
from django.contrib.auth.hashers import make_password
from django.conf import settings

def register(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            # Guardamos la contraseña correctamente
            user.password = make_password(form.cleaned_data['password'])
        
            # Generar código de verificación
            user.generate_verification_code()
      
            # Enviar correo
            send_mail(
                "Código de verificación",
                f"Tu código de verificación es: {user.verification_code}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            request.session['usuario_verificar'] = user.id
            return redirect('usuarios:verify')
        else:
            return render(request, "site/signup.html", {"form": form})
    else:
        form = RegistroForm()
    return render(request, "site/signup.html", {"form": form})

# modoficado 
def verify(request):
    user_id = request.session.get('usuario_verificar')
    if not user_id:
        messages.error(request, "No hay usuario para verificar.")
        return redirect('site_signup')

    user = CustomUser.objects.get(id=user_id)
    form = VerificacionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        codigo = form.cleaned_data['codigo']
        if user.is_code_valid(codigo, minutes_valid=1):
            user.is_active = True
            user.is_verified = True
            user.verification_code = ''
            user.code_created_at = None
            user.save()
            request.session.pop('usuario_verificar', None)
            messages.success(request, "Cuenta verificada correctamente.")
            return redirect('site_login')
        else:
            messages.error(request, "Código incorrecto o expirado.")
            return redirect('usuarios:reenviar_codigo')

    return render(request, "site/verify.html", {"form": form, "email": user.email})






def reenviar_codigo(request):
    user_id = request.session.get('usuario_verificar')
    if not user_id:
        messages.error(request, "No hay usuario para reenviar código.")
        return redirect('site_signup')

    user = CustomUser.objects.get(id=user_id)

    if request.method == "POST":
        user.generate_verification_code()
        send_mail(
            "Nuevo código de verificación",
            f"Tu nuevo código es: {user.verification_code}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, f"Se ha enviado un nuevo código a {user.email}.")
        return redirect('usuarios:verify')

    # GET → mostrar formulario
    return render(request, "site/reenviar_codigo.html")


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


def home(request):
    # 'request.user' es una instancia de CustomUser si está autenticado,
    # o de AnonymousUser si no lo está.
    if request.user.is_authenticated:
        # Lógica para usuarios registrados
        mensaje = f"¡Bienvenido, {request.user.username}!"
        # ... puedes añadir más datos del usuario aquí
    else:
        # Lógica para usuarios visitantes (anónimos)
        mensaje = "¡Bienvenido! Inicia sesión o regístrate para acceder a más funciones."
    
    return render(request, 'usuarios/templates/home.html', {'mensaje': mensaje})
