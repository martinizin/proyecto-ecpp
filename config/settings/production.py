"""
Django production settings for ECPPP project.
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

# --- Database ---------------------------------------------------------------
# Prefer DATABASE_URL when provided; otherwise keep the discrete DATABASE_*
# configuration from base.py. Reuse connections to avoid per-request overhead.
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    DATABASES = {"default": dj_database_url.parse(_database_url, conn_max_age=600)}
else:
    DATABASES["default"]["CONN_MAX_AGE"] = 600  # noqa: F405

# --- Cache (Redis) ----------------------------------------------------------
# A shared cache is required so the HU27 export rate limiter stays consistent
# across Gunicorn workers (LocMemCache would be per-process).
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "ecppp",
    }
}

# --- Static files (WhiteNoise) ---------------------------------------------
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# WhiteNoise must sit right after SecurityMiddleware.
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:  # noqa: F405
    MIDDLEWARE.insert(  # noqa: F405
        MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,  # noqa: F405
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )

# --- Security ---------------------------------------------------------------
# TLS is terminated by Caddy, which forwards X-Forwarded-Proto.
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# X_FRAME_OPTIONS inherits SAMEORIGIN from base.py — required for HU21
# inspector preview of evidence files. Do NOT override back to DENY without
# first refactoring the preview to use a separate origin or signed URLs.

# --- Logging ----------------------------------------------------------------
# Log to stdout/stderr; the container platform captures it (docker logs).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
