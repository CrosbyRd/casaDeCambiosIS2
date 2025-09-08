from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from usuarios import views as usuarios_views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazyfrom core.views import pagina_inicio_y_simulador #vista de simulacionpy

urlpatterns = [
    # --- Home ---
    path("", TemplateView.as_view(template_name="site/home.html"), name="home"),

    # --- Páginas informativas ---
    path("calculator/", TemplateView.as_view(template_name="site/calculator.html"), name="site_calculator"),
    path("how-it-works/", TemplateView.as_view(template_name="site/how-it-works.html"), name="site_how_it_works"),
    path("rates/", TemplateView.as_view(template_name="site/rates.html"), name="site_rates"),
    path("faq/", TemplateView.as_view(template_name="site/faq.html"), name="site_faq"),
    #path("calculator/", TemplateView.as_view(template_name="site/calculator.html"), name="site_calculator"),
    path("calculator/", pagina_inicio_y_simulador, name="site_calculator"),
    path("contact/", TemplateView.as_view(template_name="site/contact.html"), name="site_contact"),
    path("legal/", TemplateView.as_view(template_name="site/legal.html"), name="site_legal"),
    # NUEVO: Landing de alta (botón “Crear cuenta”)
    path("signup/", TemplateView.as_view(template_name="site/signup.html"), name="site_signup"),

    # --- Apps ---
    path("usuarios/", include("usuarios.urls")),
    path("clientes/", include("clientes.urls", namespace="clientes")),
    path("roles/", include("roles.urls", namespace="roles")),
    path("monedas/", include("monedas.urls", namespace="monedas")),
    path("cotizaciones/", include("cotizaciones.urls")),
    path("admin_panel/", include("admin_panel.urls")),

    # --- Autenticación propia (OTP + logout GET/POST) ---
    path("cuentas/login/", usuarios_views.login_view, name="login"),
    path("cuentas/otp/", usuarios_views.login_otp, name="login_otp"),
    path("cuentas/otp/reenviar/", usuarios_views.login_otp_resend, name="login_otp_resend"),
    path("cuentas/logout/", usuarios_views.logout_view, name="logout"),
    path("forgot-password/",auth_views.PasswordResetView.as_view(template_name="site/forgot-password.html",
        success_url=reverse_lazy("password_reset_done")),name="site_forgot_password",),
    path("cuentas/password_reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="site/forgot-password-done.html"), name="password_reset_done"),
    path("cuentas/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="site/reset-confirm.html"), name="password_reset_confirm"),
    path("cuentas/reset/done/",  auth_views.PasswordResetCompleteView.as_view(
        template_name="site/reset-complete.html"), name="password_reset_complete"),

    # --- Auth de Django (reset de contraseña, etc.) ---
    path("cuentas/", include("django.contrib.auth.urls")),

    # --- Admin Django ---
    path("admin/", admin.site.urls),
]
