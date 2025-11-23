from django.urls import path
from . import views

app_name = "analista_panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]