# tu_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# No necesitamos una vista de login personalizada por ahora, usamos la de Django

@login_required
def dashboard_simple(request):
    """
    Vista que solo puede ser accedida por usuarios autenticados.
    """
    return render(request, 'dashboard_simple.html')

