from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render


@login_required
def dashboard(request):
    """Dashboard del Analista: acceso solo con permiso específico.
    Patron igual al admin_panel: si no tiene permiso → redirige a 'home'.
    """
    if not request.user.has_perm("analista_panel.access_analista_dashboard"):
        return redirect("home")

    return render(request, "analista_panel/dashboard.html")