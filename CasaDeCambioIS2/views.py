# proyecto_principal/views.py
from django.shortcuts import render    #devuelve una respuesta HTML

def home(request):
    return render(request, 'home.html')