"""
Django production settings for ECPPP project.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")

# Security settings
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS inherits SAMEORIGIN from base.py — required for HU21
# inspector preview of evidence files. Do NOT override back to DENY without
# first refactoring the preview to use a separate origin or signed URLs.
