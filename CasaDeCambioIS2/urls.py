from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from core.views import pagina_inicio_y_simulador #vista de simulacionpy

urlpatterns = [
    # --- Páginas Públicas y del Sitio ---
    path("", TemplateView.as_view(template_name="site/home.html"), name="home"),
    path("rates/", TemplateView.as_view(template_name="site/rates.html"), name="site_rates"),
    path("how-it-works/", TemplateView.as_view(template_name="site/how-it-works.html"), name="site_how_it_works"),
    path("faq/", TemplateView.as_view(template_name="site/faq.html"), name="site_faq"),
    #path("calculator/", TemplateView.as_view(template_name="site/calculator.html"), name="site_calculator"),
    path("calculator/", pagina_inicio_y_simulador, name="site_calculator"),
    path("contact/", TemplateView.as_view(template_name="site/contact.html"), name="site_contact"),
    path("legal/", TemplateView.as_view(template_name="site/legal.html"), name="site_legal"),
    path("forgot-password/", TemplateView.as_view(template_name="site/forgot-password.html"), name="site_forgot_password"),

    # --- Inclusión de Apps del Proyecto ---
    path('admin/', admin.site.urls),

    # Usuarios (API + vistas)
    path('usuarios/', include('usuarios.urls')),

    # Clientes y Roles (con namespace tal como lo tenías)
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('roles/', include('roles.urls', namespace='roles')),
    
    # CORRECCIÓN: La app 'lib' no parece tener un propósito claro, la comento por ahora.
    # Si la necesitas, puedes descomentarla.
    # path("lib/", include("lib.urls")), 



    path('api/', include('usuarios.urls')),
    #path('monedas/', include('monedas.urls')),

        # Auth de Django montado en /cuentas/
    path('cuentas/', include('django.contrib.auth.urls')),

    # ⬇️ NUEVO: Monedas protegidas (rutas están dentro de la app)
    path('monedas/', include('monedas.urls', namespace='monedas')),

    path("cotizaciones/", include("cotizaciones.urls")),
    path("admin_panel/", include("admin_panel.urls")),

]
