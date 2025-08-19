from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return HttpResponse("Hola mundo xd")

def login_view(request):
    return render(request, 'login.html')
