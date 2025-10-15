"""
Django settings for CasaDeCambioIS2 project.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Seguridad / Debug ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")  # En prod: setear env
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "*"]

# --- Stripe ---
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "lib",
    "simuladores",
    "usuarios",
    "clientes",
    "roles",
    "monedas",
    "cotizaciones",
    "admin_panel",
    "core.apps.CoreConfig",
    "pagos",
    "medios_acreditacion",
    "operaciones",
    "transacciones",
    "configuracion",
    "payments",
    "ted",
    "django_extensions"
    "analista_panel",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- URLs / WSGI ---
ROOT_URLCONF = "CasaDeCambioIS2.urls"
WSGI_APPLICATION = "CasaDeCambioIS2.wsgi.application"

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Base de datos (Postgres local) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "casadecambio_db",
        "USER": "casadecambio_user",
        "PASSWORD": "una_contraseña_muy_segura",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# --- Usuario personalizado ---
AUTH_USER_MODEL = "usuarios.CustomUser"

# --- Correo saliente (Gmail con App Password de 16 caracteres) ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "globalexchangeparaguay@gmail.com")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "dhqe ofhp bhad nwhg")  # App password si no usas env
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", f"Global Exchange <{EMAIL_HOST_USER}>")

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / zona horaria ---
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Asuncion"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth redirects ---
LOGIN_URL = "/cuentas/login/"
LOGIN_REDIRECT_URL = "usuarios:login_redirect"
LOGOUT_REDIRECT_URL = "/"

# --- TED / Cotizaciones ---
# Minutos de vigencia considerados "recientes" para una cotización.
# Puedes sobreescribirlo con la variable de entorno TED_COTIZACION_VIGENCIA_MINUTES.
TED_COTIZACION_VIGENCIA_MINUTES = int(os.getenv("TED_COTIZACION_VIGENCIA_MINUTES", "15"))

# En desarrollo, permite operar con cotizaciones vencidas si se activa.
# TED_ALLOW_STALE_RATES=true en el entorno para activarlo.
TED_ALLOW_STALE_RATES = os.getenv("TED_ALLOW_STALE_RATES", "true").strip().lower() in ("1", "true", "yes", "on")
