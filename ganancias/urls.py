from django.urls import path
from . import views

app_name = 'ganancias'

urlpatterns = [
    path('dashboard/', views.dashboard_ganancias, name='dashboard_ganancias'),
]
