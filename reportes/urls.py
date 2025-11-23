from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.panel_reportes, name='panel_reportes'),

    # Ganancias
    path('ganancias/', views.reporte_ganancias, name='reporte_ganancias'),
    path('ganancias/pdf/', views.reporte_ganancias_pdf, name='reporte_ganancias_pdf'),
    path('ganancias/excel/', views.reporte_ganancias_excel, name='reporte_ganancias_excel'),

    # Transacciones
    path('transacciones/', views.reporte_transacciones, name='reporte_transacciones'),
    path('transacciones/pdf/', views.reporte_transacciones_pdf, name='reporte_transacciones_pdf'),
    path('transacciones/excel/', views.reporte_transacciones_excel, name='reporte_transacciones_excel'),
]
