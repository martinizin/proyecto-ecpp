"""
Django base settings for ECPPP project.
Shared configuration inherited by development.py and production.py.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    # Project apps
    "apps.usuarios",
    "apps.academico",
    "apps.calificaciones",
    "apps.asistencia",
    "apps.solicitudes",
    "apps.secretaria",
    "apps.notificaciones",
    "apps.copilot",
    "apps.reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.usuarios.presentation.middleware.ForzarCambioPasswordMiddleware",
    "apps.usuarios.presentation.middleware.SessionTimeoutMiddleware",  # HU31
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Allow same-origin iframes so HU21 inspector dashboard can preview media
# files (PDFs, images) via <iframe src="/media/..."> and <img src="/media/...">.
# Cross-origin framing is still blocked, which is the real clickjacking vector.
X_FRAME_OPTIONS = "SAMEORIGIN"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — PostgreSQL only, no SQLite fallback.
# Defaults razonables para CI/dev local; producción debe setear los env vars
# explícitamente. Mantenemos DJANGO_SECRET_KEY estricto (línea 17) porque ahí
# un default sería un agujero de seguridad.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DATABASE_NAME", "ecppp_test"),
        "USER": os.environ.get("DATABASE_USER", "test_user"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "test_pass"),
        "HOST": os.environ.get("DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
    }
}

# Custom user model — MUST be set before first migration
AUTH_USER_MODEL = "usuarios.Usuario"

# Authentication backends — ECPPPAuthBackend handles email+password+tipo_usuario login,
# ModelBackend is the fallback for Django Admin (which authenticates by username+password).
AUTHENTICATION_BACKENDS = [
    "apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Login / Logout URLs
LOGIN_URL = "/usuarios/login/"
LOGIN_REDIRECT_URL = "/usuarios/dashboard/"
LOGOUT_REDIRECT_URL = "/usuarios/login/"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "apps.usuarios.infrastructure.password_validators.UppercaseValidator",
    },
    {
        "NAME": "apps.usuarios.infrastructure.password_validators.SymbolValidator",
    },
    {
        "NAME": (
            "apps.usuarios.infrastructure.password_validators" ".UserAttributeContainmentValidator"
        ),
    },
]

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# HU31 — Session timeout (inactividad). SESSION_COOKIE_AGE queda como
# backstop defense-in-depth; la SessionTimeoutMiddleware usa su propio
# reloj contra ``request.session['last_activity']`` (ver R10 spec).
SESSION_TIMEOUT_SECONDS = 1200  # 20 min de inactividad = logout
SESSION_WARNING_SECONDS = 120   # pop-up de aviso a los 18 min
SESSION_UPDATE_INTERVAL_SECONDS = 60  # throttle del write de last_activity

# Session timeout (HU31) — cierre por inactividad. El cookie age de
# arriba es un backstop absoluto y se mantiene en 3600s; este timeout
# es la fuente de verdad para "cuánto tiempo puede estar idle un
# usuario autenticado". SESSION_TIMEOUT_SECONDS=0 desactiva la feature.
SESSION_TIMEOUT_SECONDS = int(os.environ.get("SESSION_TIMEOUT_SECONDS", "1200"))  # 20 min
SESSION_WARNING_SECONDS = int(os.environ.get("SESSION_WARNING_SECONDS", "120"))  # 2 min

# Password reset
PASSWORD_RESET_TIMEOUT = 1800  # 30 minutos

# App-specific constants — Auth & OTP
OTP_EXPIRATION_MINUTES = 10
ACCOUNT_LOCKOUT_MINUTES = 15
MAX_LOGIN_ATTEMPTS = 5

# ============================================================
# Validaciones de negocio — Académico (QA HU21 V1-V4)
# ============================================================
PARALELO_CAPACIDAD_MAXIMA = 50  # V3 — cupo máximo por paralelo
PERIODO_DURACION_MIN_MESES = 4  # V4 — duración mínima de periodo
PERIODO_DURACION_MAX_MESES = 7  # V4 — duración máxima de periodo
HORAS_LECTIVAS_MAX = 60  # V2 — tope de horas lectivas por asignatura/licencia
HORAS_LECTIVAS_MIN = 20  # V2b — mínimo de horas lectivas por asignatura/licencia

# Internationalization
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files (user uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email configuration — SMTP
# Default: Django's standard SMTP backend (works with Gmail, Mailgun, etc.)
# For Brevo: set EMAIL_BACKEND=apps.usuarios.infrastructure.smtp_backend.BrevoEmailBackend
# in .env (Brevo South America needs hostname verification disabled).
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@ecppp.edu.ec")

# Logo URL for email templates
LOGO_URL = os.environ.get("LOGO_URL", "https://i.imgur.com/EPsrSix.png")

# Copilot / OpenAI settings.
# El default "sk-test-dummy-key-not-used-for-real-calls" es un placeholder
# suficiente para que el SDK de openai se instancie sin tirar Missing credentials
# (el SDK moderno valida en el constructor). Producción debe setear OPENAI_API_KEY
# explícitamente vía env var. Los tests que mockean el SDK no hacen llamadas
# reales, así que el valor dummy no afecta su comportamiento.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-test-dummy-key-not-used-for-real-calls")
COPILOT_MODEL = os.environ.get("COPILOT_MODEL", "gpt-4o-mini")

# Copilot content moderation (HU22 + copilot-content-moderation, PR 1a)
# Feature flag maestro: cuando es False, todo el pipeline de moderación
# (input lista + input OpenAI fallback + output OpenAI check) se bypasea.
# Default True: salimos defendidos, no indefensos.
COPILOT_MODERATION_ENABLED = os.environ.get("COPILOT_MODERATION_ENABLED", "True") == "True"
# Ruta al JSON de allow-list (frases académicas que relajan la severidad strong).
# Si el archivo no existe o tiene JSON inválido, el loader loggea WARNING y
# opera con la lista curada únicamente.
# PR 1b: el archivo se renombró a ``allowlist_es.json`` (más descriptivo que
# el placeholder ``copilot_moderation_allowlist.json`` de PR 1a). El default
# apunta al archivo que PR 1b crea en ``apps/copilot/data/``.
COPILOT_MODERATION_ALLOWLIST_PATH = BASE_DIR / "apps" / "copilot" / "data" / "allowlist_es.json"
# OpenAI Moderation API — model y timeout (PR 1b).
# ``omni-moderation-latest`` es el modelo multilingüe más reciente y el default
# locked por design.md §Configuration.
COPILOT_MODERATION_MODEL = os.environ.get("COPILOT_MODERATION_MODEL", "omni-moderation-latest")
# Timeout para llamadas a la API de moderación, en milisegundos. El default
# 1500 ms (1.5 s) balancea latencia vs disponibilidad — la OpenAI Moderation
# API tiene p50 ~200 ms; 1.5 s deja margen para redes lentas sin penalizar
# la UX. El constructor de ``OpenAIModerationClient`` convierte a segundos.
COPILOT_MODERATION_OPENAI_TIMEOUT_MS = int(
    os.environ.get("COPILOT_MODERATION_OPENAI_TIMEOUT_MS", "1500")
)
# Modos de fallo (hard-coded en el servicio, no se exponen como setting aún):
# - input  → "OPEN"  (REQ-009: preferimos falsos negativos sobre falsos positivos)
# - output → "SKIP"  (REQ-009: la respuesta del LLM se devuelve tal cual)
COPILOT_MODERATION_INPUT_FAIL_MODE = os.environ.get("COPILOT_MODERATION_INPUT_FAIL_MODE", "OPEN")
COPILOT_MODERATION_OUTPUT_FAIL_MODE = os.environ.get("COPILOT_MODERATION_OUTPUT_FAIL_MODE", "SKIP")

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
