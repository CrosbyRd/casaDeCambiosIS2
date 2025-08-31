# usuarios/views.py

# --- Imports necesarios (solo los que se usan) ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required # <--- Importante para proteger vistas

# --- Modelos y Formularios ---
from .models import CustomUser
from .forms import RegistroForm, VerificacionForm
from clientes.models import Cliente

# --- Vistas de Autoregistro y Verificación (Estas se quedan igual) ---

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
            # Redirigimos a la nueva URL de login de Django
            return redirect('login') 
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

# --- Vistas de Administración (Ahora protegidas) ---

@login_required
def admin_panel(request):
    # Buena práctica: verificar si el usuario es staff/admin
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para acceder a esta página.")
        return redirect('home') # Redirigir a la página de inicio
    return render(request, 'admin_panel:dashboard')

@login_required
def listar_usuarios(request):
    if not request.user.is_staff:
        return redirect('home')
    usuarios = CustomUser.objects.all().prefetch_related('clientes', 'roles')
    todos_clientes = Cliente.objects.all()
    return render(request, 'usuarios/listar_usuarios.html', {
        'usuarios': usuarios,
        'todos_clientes': todos_clientes
    })

@login_required
def agregar_cliente(request, user_id, cliente_id):
    if not request.user.is_staff:
        return redirect('home')
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.add(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' agregado a {user.email}.")
    return redirect('usuarios:listar_usuarios')

@login_required
def quitar_cliente(request, user_id, cliente_id):
    if not request.user.is_staff:
        return redirect('home')
    user = get_object_or_404(CustomUser, id=user_id)
    cliente = get_object_or_404(Cliente, id_cliente=cliente_id)
    user.clientes.remove(cliente)
    messages.success(request, f"Cliente '{cliente.nombre}' quitado de {user.email}.")
    return redirect('usuarios:listar_usuarios')