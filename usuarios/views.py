from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .utils import SESSION_KEY, get_cliente_activo
from .models import CustomUser
from .forms import RegistroForm, VerificacionForm
from clientes.models import Cliente
from roles.models import Role # Importar el modelo Role
from transacciones.models import Transaccion
from django.contrib.auth import get_user_model

# ----------------------------
# Registro + verificación de cuenta
# ----------------------------

def register(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.email = form.cleaned_data["email"].lower().strip()
            user.first_name = form.cleaned_data["first_name"].strip()
            user.last_name = form.cleaned_data["last_name"].strip()
            user.password = make_password(form.cleaned_data["password"])
            user.save()

            # Asignar el rol de "Cliente" por defecto
            try:
                cliente_role = Role.objects.get(name="Cliente")
                user.roles.add(cliente_role)
            except Role.DoesNotExist:
                # Opcional: Manejar el caso en que el rol no exista.
                # Por ahora, simplemente lo ignoramos, pero podrías loggear un error.
                pass

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
    return render(request, "site/signup.html", {"form": form})


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

    # Bypass OTP para el usuario administrador en desarrollo y para usuarios con rol 'Cliente_Dev_OTP_Bypass'
    admin_email = "globalexchangea2@gmail.com"
    if (settings.DEBUG and user.email == admin_email) or (settings.DEBUG and user.roles.filter(name="Cliente_Dev_OTP_Bypass").exists()):
        login(request, user)
        next_url = request.session.pop("pending_login_next", None)
        return redirect(next_url or "usuarios:login_redirect")

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
    if request.method in ("GET", "POST"):
        logout(request)
        messages.info(request, "Sesión cerrada correctamente.")
        return redirect("home")
    return redirect("home")


def login_redirect(request):
    user = request.user

    if not user.is_authenticated:
        return redirect("login")
    
    # ROL DE ADMINISTRADOR
    if user.roles.filter(name__iexact="Administrador").exists():
        return redirect("admin_panel:dashboard")

    # ROL DE ANALISTA
    if user.roles.filter(name__iexact="Analista").exists() \
       or user.has_perm("analista_panel.access_analista_dashboard"):
        return redirect("analista_panel:dashboard")

    messages.success(request, "¡Bienvenido!")
    return redirect("usuarios:dashboard")


from transacciones.models import Transaccion

@login_required
def dashboard(request):
    
    # 1. OBTENER el cliente activo
    cliente_activo = get_cliente_activo(request)
    
    # 2. Corregir la consulta de transacciones
    if cliente_activo:
        # Filtramos por el objeto Cliente activo. ¡ESTA ES LA CORRECCIÓN CLAVE!
        transacciones = Transaccion.objects.filter(
            cliente=cliente_activo # ✅ CORRECTO: Filtra por la instancia de Cliente
        ).order_by('-fecha_creacion')[:5]
    else:
        # Si no hay cliente activo, el usuario debería ir a seleccionarlo.
        # Mientras tanto, mostramos transacciones vacías.
        transacciones = Transaccion.objects.none() 

    # 3. Renderizar
    return render(
        request,
        "usuarios/dashboard.html",
        {'transacciones': transacciones, 'cliente': cliente_activo}
    )


@login_required
def admin_panel(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect("home")
    return redirect("admin_panel:dashboard")


@login_required
def listar_usuarios(request):
    if not request.user.has_perm("usuarios.access_user_client_management"):
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
    if not request.user.has_perm("usuarios.access_user_client_management"):
        return redirect("home")
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.add(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' agregado a {user.email}.")
    return redirect("usuarios:listar_usuarios")


@login_required
def quitar_cliente(request, user_id, cliente_id):
    if not request.user.has_perm("usuarios.access_user_client_management"):
        return redirect("home")
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.remove(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' quitado de {user.email}.")
    return redirect("usuarios:listar_usuarios")


@login_required
def seleccionar_cliente(request):
    
        # 🚨 SOLUCIÓN: Cargar el CustomUser fresco directamente de la DB
    try:
        User = get_user_model()
        user = User.objects.get(pk=request.user.pk)
    except User.DoesNotExist:
        # Si falla la recarga, el usuario debe desloguearse.
        messages.error(request, "Error de sesión: Usuario no encontrado.")
        return redirect('logout') # O a donde te dirija el logout
    
    clientes = user.clientes.all()

    if not clientes.exists():
        messages.warning(request, "Aún no tenés clientes asociados a tu usuario.")
        return render(request, "usuarios/seleccionar_cliente.html", {"clientes": clientes})

    if request.method == "POST":
        cid = request.POST.get("cliente_id")
        try:
            cliente = clientes.get(pk=cid)
        except Exception:
            messages.error(request, "Cliente inválido.")
        else:
            request.session[SESSION_KEY] = str(cliente.pk)
            messages.success(request, f"Cliente activo: {cliente}.")
            next_url = request.GET.get("next") or "usuarios:dashboard"
            return redirect(next_url)

    return render(request, "usuarios/seleccionar_cliente.html", {"clientes": clientes})
