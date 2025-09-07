from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from .models import CustomUser
from .forms import RegistroForm, VerificacionForm
from clientes.models import Cliente


# ----------------------------
# Registro + verificación de cuenta
# ----------------------------

def register(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.password = make_password(form.cleaned_data["password"])
            user.save()

            user.generate_verification_code()
            send_mail(
                "Código de verificación",
                f"Tu código de verificación es: {user.verification_code}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            request.session["email_verificacion"] = user.email
            return redirect("usuarios:verify")
    else:
        form = RegistroForm()
    return render(request, "site/register.html", {"form": form})


def verify(request):
    email = request.session.get("email_verificacion")
    if not email:
        messages.error(request, "Sesión de verificación inválida. Por favor, regístrate de nuevo.")
        return redirect("usuarios:register")

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        messages.error(request, "El usuario no existe.")
        return redirect("usuarios:register")

    form = VerificacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        codigo = form.cleaned_data["codigo"]
        if user.is_code_valid(codigo, minutes_valid=5):
            user.is_active = True
            user.is_verified = True
            user.verification_code = None
            user.code_created_at = None
            user.save()
            request.session.pop("email_verificacion", None)
            messages.success(request, "¡Cuenta verificada correctamente! Ya puedes iniciar sesión.")
            return redirect("login")
        else:
            messages.error(request, "Código incorrecto o expirado.")

    return render(request, "site/verify.html", {"form": form, "email": user.email})


def reenviar_codigo(request):
    email = request.session.get("email_verificacion")
    if not email:
        messages.error(request, "No hay una sesión de verificación activa.")
        return redirect("usuarios:register")

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
    return redirect("usuarios:verify")


# ----------------------------
# Login con OTP previo
# ----------------------------

def login_view(request):
    if request.method == "GET":
        return render(request, "registration/login.html")

    email = (request.POST.get("username") or "").strip().lower()
    password = request.POST.get("password") or ""
    next_url = request.POST.get("next") or request.GET.get("next")

    user = authenticate(request, username=email, password=password)
    if user is None:
        messages.error(request, "Correo o contraseña inválidos.")
        return render(request, "registration/login.html", status=401)

    if not user.is_active:
        messages.error(request, "Tu cuenta no está verificada. Verifica tu correo para activarla.")
        return redirect("login")

    user.generate_verification_code()
    send_mail(
        "Tu código de acceso",
        f"Tu código de verificación es: {user.verification_code}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

    request.session["pending_login_user_id"] = user.id
    if next_url:
        request.session["pending_login_next"] = next_url

    messages.info(request, f"Hemos enviado un código a {user.email}.")
    return redirect("login_otp")


def login_otp(request):
    uid = request.session.get("pending_login_user_id")
    if not uid:
        messages.info(request, "Inicia sesión para continuar.")
        return redirect("login")

    user = CustomUser.objects.filter(id=uid).first()
    if not user:
        request.session.pop("pending_login_user_id", None)
        return redirect("login")

    if request.method == "POST":
        code = (request.POST.get("codigo") or "").strip()
        if user.is_code_valid(code, minutes_valid=5):
            user.verification_code = None
            user.code_created_at = None
            user.save(update_fields=["verification_code", "code_created_at"])
            login(request, user)

            next_url = request.session.pop("pending_login_next", None)
            request.session.pop("pending_login_user_id", None)
            # Mensaje de bienvenida lo dejamos en login_redirect para no duplicar
            return redirect(next_url or "usuarios:login_redirect")
        else:
            messages.error(request, "Código incorrecto o expirado.")

    return render(request, "registration/verify-code.html", {"email": user.email})


def login_otp_resend(request):
    uid = request.session.get("pending_login_user_id")
    if not uid:
        return redirect("login")

    user = get_object_or_404(CustomUser, id=uid)
    user.generate_verification_code()
    send_mail(
        "Tu código de acceso",
        f"Tu código de verificación es: {user.verification_code}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    messages.success(request, f"Enviamos un nuevo código a {user.email}.")
    return redirect("login_otp")


# ----------------------------
# Logout (GET/POST) y redirecciones
# ----------------------------

def logout_view(request):
    """Cierra sesión aceptando GET o POST y redirige al inicio."""
    if request.method in ("GET", "POST"):
        logout(request)
        messages.info(request, "Sesión cerrada correctamente.")
        return redirect("home")
    # Cualquier otro método no permitido:
    return redirect("home")


def login_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("admin_panel:dashboard")
    messages.success(request, "¡Bienvenido!")
    return redirect("usuarios:dashboard")


@login_required
def dashboard(request):
    return render(request, "usuarios/dashboard.html")


@login_required
def admin_panel(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")
    return redirect("admin_panel:dashboard")


@login_required
def listar_usuarios(request):
    if not request.user.is_staff:
        return redirect("home")
    usuarios = CustomUser.objects.all().prefetch_related("clientes", "roles")
    todos_clientes = Cliente.objects.all()
    return render(
        request,
        "usuarios/listar_usuarios.html",
        {"usuarios": usuarios, "todos_clientes": todos_clientes},
    )


@login_required
def agregar_cliente(request, user_id, cliente_id):
    if not request.user.is_staff:
        return redirect("home")
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.add(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' agregado a {user.email}.")
    return redirect("usuarios:listar_usuarios")


@login_required
def quitar_cliente(request, user_id, cliente_id):
    if not request.user.is_staff:
        return redirect("home")
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.remove(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' quitado de {user.email}.")
    return redirect("usuarios:listar_usuarios")
