from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Home público
    path("", TemplateView.as_view(template_name="site/home.html"), name="home"),

    # Páginas públicas
    path("rates/", TemplateView.as_view(template_name="site/rates.html"), name="site_rates"),
    path("how-it-works/", TemplateView.as_view(template_name="site/how-it-works.html"), name="site_how_it_works"),
    path("faq/", TemplateView.as_view(template_name="site/faq.html"), name="site_faq"),
    path("calculator/", TemplateView.as_view(template_name="site/calculator.html"), name="site_calculator"),
    path("contact/", TemplateView.as_view(template_name="site/contact.html"), name="site_contact"),
    path("legal/", TemplateView.as_view(template_name="site/legal.html"), name="site_legal"),
    path("forgot-password/", TemplateView.as_view(template_name="site/forgot-password.html"), name="site_forgot_password"),
    path("login/", TemplateView.as_view(template_name="site/login.html"), name="site_login"),
    path("signup/", TemplateView.as_view(template_name="site/signup.html"), name="site_signup"),
    path("verify-code/", TemplateView.as_view(template_name="site/verify-code.html"), name="site_verify_code"),

    # NUEVO: Dashboard post-login
    path("dashboard/", TemplateView.as_view(template_name="site/dashboard.html"), name="dashboard"),

    # Tu app
    path("lib/", include("lib.urls")),
    path("admin/", admin.site.urls),

    # API
    path("api/auth/", include("usuarios.urls")),  # incluye register, me, login-step1, verify-code
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
