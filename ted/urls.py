from django.urls import path
from . import views

app_name = "ted"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("operar/", views.operar, name="operar"),
    path("ticket/", views.ticket_popup, name="ticket"),
    path("cheque/", views.cheque_mock, name="cheque_mock"),
]
