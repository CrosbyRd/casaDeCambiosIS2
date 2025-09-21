from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from usuarios import views as usuarios_views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from core.views import pagina_inicio_y_simulador, site_home, site_rates

urlpatterns = [
    # Home dinámico
    path("", site_home, name="home"),

    # Páginas informativas
    path("how-it-works/", TemplateView.as_view(template_name="site/how-it-works.html"), name="site_how_it_works"),
    path("rates/", site_rates, name="site_rates"),
    path("faq/", TemplateView.as_view(template_name="site/faq.html"), name="site_faq"),
    path("calculator/", pagina_inicio_y_simulador, name="site_calculator"),
    path("contact/", TemplateView.as_view(template_name="site/contact.html"), name="site_contact"),
    path("legal/", TemplateView.as_view(template_name="site/legal.html"), name="site_legal"),
    path("signup/", TemplateView.as_view(template_name="site/signup.html"), name="site_signup"),

    # Apps
    path("usuarios/", include("usuarios.urls")),
    path("clientes/", include(("clientes.urls", "clientes"), namespace="clientes")),
    path("roles/", include(("roles.urls", "roles"), namespace="roles")),
    path("monedas/", include(("monedas.urls", "monedas"), namespace="monedas")),
    path("cotizaciones/", include("cotizaciones.urls")),
    path("pagos/", include(("pagos.urls", "pagos"), namespace="pagos")),
    path("admin_panel/", include("admin_panel.urls")),

    # Autenticación (OTP + reset)
    path("cuentas/login/", usuarios_views.login_view, name="login"),
    path("cuentas/otp/", usuarios_views.login_otp, name="login_otp"),
    path("cuentas/otp/reenviar/", usuarios_views.login_otp_resend, name="login_otp_resend"),
    path("cuentas/logout/", usuarios_views.logout_view, name="logout"),

    # Password reset (dos nombres por compatibilidad con templates existentes)
    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="site/forgot-password.html",
            success_url=reverse_lazy("password_reset_done")
        ),
        name="password_reset",
    ),
    path(  # alias usado por login.html
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="site/forgot-password.html",
            success_url=reverse_lazy("password_reset_done")
        ),
        name="site_forgot_password",
    ),
    path(
        "cuentas/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="site/forgot-password-done.html"),
        name="password_reset_done",
    ),
    path(
        "cuentas/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="site/reset-confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "cuentas/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="site/reset-complete.html"),
        name="password_reset_complete",
    ),


    path("medios-acreditacion/", include("medios_acreditacion.urls")),

    # Admin de Django
    path("admin/", admin.site.urls),

    
]