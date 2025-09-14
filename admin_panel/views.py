# admin_panel/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# --- Función auxiliar para verificar si es admin ---
def es_admin(user):
    return user.is_authenticated and user.is_staff

# --- Vista protegida ---
@login_required

def dashboard(request):
    if not request.user.is_staff:  # redundante pero explícito
        messages.error(request, "No tienes permiso para acceder al panel de administración.")
        return redirect("home")  # o a donde quieras redirigirlos
    return render(request, "admin_panel/dashboard.html")
