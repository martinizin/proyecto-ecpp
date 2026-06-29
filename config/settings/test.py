"""
Django settings for the test suite.
Uses SQLite so no CREATEDB privilege is needed on PostgreSQL.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up password hashing during tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable email sending
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
