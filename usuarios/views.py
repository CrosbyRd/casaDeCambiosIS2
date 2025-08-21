from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

from .serializers import UserSerializer, RegisterSerializer
from .models import CustomUser, EmailLoginCode

# Vista para el registro de usuarios
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

# Vista para obtener los datos del usuario logueado
class CurrentUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

# --- MFA paso 1: validar credenciales y enviar código por email ---
class LoginStep1View(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", "")).strip()

        if not username or not password:
            return Response({"detail": "Faltan credenciales."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Usuario o contraseña inválidos."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({"detail": "La cuenta está inactiva."}, status=status.HTTP_403_FORBIDDEN)

        if not user.email:
            return Response({"detail": "Este usuario no tiene un e-mail configurado."}, status=status.HTTP_400_BAD_REQUEST)

        # Crear código y registro
        code_obj = EmailLoginCode.create_for_user(user, lifetime_minutes=10)

        # Enviar email
        subject = "Tu código de acceso — Global Exchange"
        body = (
            f"Hola {user.first_name or user.username},\n\n"
            f"Tu código de acceso es: {code_obj.code}\n"
            f"Este código expira en 10 minutos.\n\n"
            f"Si no intentaste iniciar sesión, ignora este mensaje."
        )
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        # Pequeña máscara para mostrar destino
        def mask_email(e: str) -> str:
            try:
                local, domain = e.split("@", 1)
                if len(local) <= 2:
                    local_mask = local[0] + "****"
                else:
                    local_mask = local[0] + "****" + local[-1]
                return f"{local_mask}@{domain}"
            except Exception:
                return "correo registrado"

        return Response(
            {
                "mfa_token": str(code_obj.mfa_token),
                "email_mask": mask_email(user.email),
                "detail": "Código enviado al correo registrado.",
            },
            status=status.HTTP_200_OK,
        )

# --- MFA paso 2: verificar código y emitir JWT ---
class VerifyCodeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken

        mfa_token = str(request.data.get("mfa_token", "")).strip()
        code = str(request.data.get("code", "")).strip()

        if not mfa_token or not code:
            return Response({"detail": "Faltan datos."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            code_obj = EmailLoginCode.objects.select_related("user").get(mfa_token=mfa_token)
        except EmailLoginCode.DoesNotExist:
            return Response({"detail": "Sesión MFA no encontrada o expirada."}, status=status.HTTP_400_BAD_REQUEST)

        if code_obj.used:
            return Response({"detail": "El código ya fue utilizado. Inicia el proceso nuevamente."}, status=status.HTTP_400_BAD_REQUEST)

        if code_obj.is_expired():
            return Response({"detail": "El código expiró. Vuelve a iniciar sesión."}, status=status.HTTP_400_BAD_REQUEST)

        if code_obj.attempts >= 5:
            return Response({"detail": "Demasiados intentos. Vuelve a iniciar sesión."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if code != code_obj.code:
            code_obj.attempts += 1
            code_obj.save(update_fields=["attempts"])
            remaining = max(0, 5 - code_obj.attempts)
            return Response({"detail": f"Código inválido. Intentos restantes: {remaining}."}, status=status.HTTP_400_BAD_REQUEST)

        # Éxito: marcar usado y emitir JWT
        user = code_obj.user
        code_obj.mark_used()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "detail": "Verificación correcta."
            },
            status=status.HTTP_200_OK,
        )

# (Vista 'home' antigua conservada por compatibilidad si la usas en algún lado)
def home(request):
    from django.shortcuts import render
    if request.user.is_authenticated:
        mensaje = f"¡Bienvenido, {request.user.username}!"
    else:
        mensaje = "¡Bienvenido! Inicia sesión o regístrate para acceder a más funciones."
    return render(request, 'usuarios/templates/home.html', {'mensaje': mensaje})
