# admin_panel/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# --- Vista protegida ---
@login_required
def dashboard(request):
    if not request.user.has_perm("admin_panel.access_admin_dashboard"):
        return redirect("home")   # o cualquier otra página
    return render(request, "admin_panel/dashboard.html")