from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
urlpatterns = [
    # --- Páginas Públicas y del Sitio ---
    path("", TemplateView.as_view(template_name="site/home.html"), name="home"),
    path("rates/", TemplateView.as_view(template_name="site/rates.html"), name="site_rates"),
    path("how-it-works/", TemplateView.as_view(template_name="site/how-it-works.html"), name="site_how_it_works"),
    path("faq/", TemplateView.as_view(template_name="site/faq.html"), name="site_faq"),
    path("calculator/", TemplateView.as_view(template_name="site/calculator.html"), name="site_calculator"),
    path("contact/", TemplateView.as_view(template_name="site/contact.html"), name="site_contact"),
    path("legal/", TemplateView.as_view(template_name="site/legal.html"), name="site_legal"),
    # CORRECCIÓN: Se elimina el path("signup/", ...) de aquí porque ahora lo maneja la app 'usuarios'.
    path("forgot-password/", TemplateView.as_view(template_name="site/forgot-password.html"), name="site_forgot_password"),
    path("login/", TemplateView.as_view(template_name="site/login.html"), name="site_login"),

    # --- Inclusión de Apps del Proyecto ---
    path('admin/', admin.site.urls),
    
    # MERGE: Cambiamos el prefijo de 'api/auth/' a 'usuarios/' porque maneja tanto la API como las vistas web.
    # Esto hace que tus URLs sean más intuitivas. Ej: /usuarios/register/, /usuarios/api/me/
    path('usuarios/', include('usuarios.urls')), 
    
    path('clientes/', include('clientes.urls', namespace='clientes')),
    
    # MERGE: Añadimos la inclusión de la app 'roles' de la rama entrante.
    path('roles/', include('roles.urls', namespace='roles')),
     path('documentacion/', TemplateView.as_view(template_name='documentacion/documentacion.html'), name='documentacion'),
    
    # CORRECCIÓN: La app 'lib' no parece tener un propósito claro, la comento por ahora.
    # Si la necesitas, puedes descomentarla.
    # path("lib/", include("lib.urls")), 

    # --- Endpoints de Autenticación para la API (JWT) ---
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    path('api/', include('usuarios.urls'))
]