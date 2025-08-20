from django.urls import path
from lib.views import login_view

from . import views

urlpatterns = [
    path('', login_view, name='login_page'), # <-- Añade esta línea
    
]
