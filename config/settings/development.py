"""
Django development settings for ECPPP project.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Email — imprime en consola en vez de enviar por SMTP
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
