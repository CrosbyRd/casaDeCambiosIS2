from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from usuarios import views as usuarios_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # --- Home ---
    path("", TemplateView.as_view(template_name="site/home.html"), name="home"),

    # --- Páginas informativas ---
    path("calculator/", TemplateView.as_view(template_name="site/calculator.html"), name="site_calculator"),
    path("how-it-works/", TemplateView.as_view(template_name="site/how-it-works.html"), name="site_how_it_works"),
    path("rates/", TemplateView.as_view(template_name="site/rates.html"), name="site_rates"),
    path("faq/", TemplateView.as_view(template_name="site/faq.html"), name="site_faq"),
    path("contact/", TemplateView.as_view(template_name="site/contact.html"), name="site_contact"),
    path("legal/", TemplateView.as_view(template_name="site/legal.html"), name="site_legal"),
    path("forgot-password/", TemplateView.as_view(template_name="site/forgot-password.html"), name="site_forgot_password"),

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
    path("cuentas/logout/", usuarios_views.logout_view, name="logout"),  # <- nuestro logout

    # --- Auth de Django (reset de contraseña, etc.) ---
        # --- Reset de contraseña (personalizado con nuestros templates) ---
    path(
        "cuentas/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "cuentas/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "cuentas/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "cuentas/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # --- Admin Django ---
    path("admin/", admin.site.urls),
]
