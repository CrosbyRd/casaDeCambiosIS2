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
# Claves de API (pk_test_... y sk_test_...)
# Estas claves se leen desde las variables de entorno (.env en local, Config Vars en Heroku)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000") # Carga SITE_URL desde .env con un valor por defecto

# --- SECRETO DE WEBHOOK DE STRIPE ---
# Esta es la clave MÁS CRÍTICA para la configuración de producción.
#
# !! IMPORTANTE !!
# En DESARROLLO LOCAL, este valor se obtiene de la terminal al correr:
# $ stripe listen --forward-to localhost:8000/payments/webhook/
# (La clave 'whsec_...' que imprime ese comando debe ir en el .env)
#
# En PRODUCCIÓN (Heroku), esta clave DEBE ser diferente. Se obtiene desde:
# 1. Ir al Dashboard de Stripe (Modo de Prueba).
# 2. Ir a Developers > Webhooks.
# 3. Crear un "Endpoint" que apunte a la URL pública de Heroku:
#    https://[tu-app].herokuapp.com/payments/webhook/
# 4. Stripe generará un "Signing secret" (whsec_...) para ESE endpoint.
# 5. Esa es la clave que DEBE ir en las "Config Vars" de Heroku.
#
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") # Añadir esta línea

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
    "admin_panel",
    "core.apps.CoreConfig",
    "pagos",
    "medios_acreditacion",
    'notificaciones',
    "operaciones",
    "transacciones",
    "configuracion",
    "payments",
    "ted",
    "django_extensions",
    "analista_panel",
    "facturacion_electronica", # Nueva app para facturación electrónica
    "ganancias", # Nueva app para el módulo de ganancias
    "widget_tweaks",
    "cotizaciones.apps.CotizacionesConfig",

    'reportes',

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

# --- CELERY SETTINGS ---NOTIFICACION DE TASAS
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# --- TED / Cotizaciones ---
# Minutos de vigencia considerados "recientes" para una cotización.
TED_COTIZACION_VIGENCIA_MINUTES = int(os.getenv("TED_COTIZACION_VIGENCIA_MINUTES", "15"))
# En desarrollo, permite operar con cotizaciones vencidas si se activa.
TED_ALLOW_STALE_RATES = os.getenv("TED_ALLOW_STALE_RATES", "true").strip().lower() in ("1", "true", "yes", "on")
TED_ALLOWED_STATES = {
    "deposito": {"pendiente_deposito_tauser", "pendiente_pago_cliente"},
    "retiro": {"pendiente_retiro_tauser", "pendiente_pago_cliente"}, }
TED_REQUIRE_KEY = False


# --- Configuración de Facturación Electrónica (FacturaSegura) ---
# Los valores se toman del .env; en DEBUG usa *_TEST, en PROD usa *_PROD.
FACTURASEGURA = {
    "BASE_URL": os.getenv(
        "FACTURASEGURA_API_URL_TEST" if DEBUG else "FACTURASEGURA_API_URL_PROD",
        "https://apitest.facturasegura.com.py/misife00/v1/esi"
    ).rstrip("/"),
    "LOGIN_URL": os.getenv(
        "FACTURASEGURA_LOGIN_URL_TEST" if DEBUG else "FACTURASEGURA_LOGIN_URL_PROD",
        "https://apitest.facturasegura.com.py/login?include_auth_token"
    ),
    "TIMEOUT": int(os.getenv("FACTURASEGURA_TIMEOUT", 30)),
    "RETRIES": int(os.getenv("FACTURASEGURA_RETRIES", 3)),
    "SIMULATION_MODE": os.getenv("FACTURASEGURA_SIMULATION_MODE", "true").strip().lower() in ("1", "true", "yes", "on"),
    "EMAIL": os.getenv("FACTURASEGURA_ESI_EMAIL"),
    "PASSWORD": os.getenv("FACTURASEGURA_ESI_PASSWORD"),
}
