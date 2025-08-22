# roles/urls.py
from django.urls import path
from .views import RoleListCreateView, RoleDetailView, role_panel

app_name = "roles"

urlpatterns = [
    path('', RoleListCreateView.as_view(), name='role-list-create'),
    path('<int:pk>/', RoleDetailView.as_view(), name='role-detail'),

    path('panel/', role_panel, name='role-panel'),
]