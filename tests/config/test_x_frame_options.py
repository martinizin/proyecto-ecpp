"""Regression tests for X_FRAME_OPTIONS configuration.

Context: HU21 added <iframe> preview for justification evidence (PDFs).
Django's default X_FRAME_OPTIONS=DENY blocks same-origin iframes too,
which broke the preview. We use SAMEORIGIN in base settings so the
preview works in dev AND prod, while still blocking cross-origin
clickjacking attempts.
"""

from importlib import import_module, reload

import pytest
from django.conf import settings
from django.test import Client


def test_base_setting_is_sameorigin():
    """Active settings (development inherits from base) must allow same-origin framing."""
    assert settings.X_FRAME_OPTIONS == "SAMEORIGIN", (
        "X_FRAME_OPTIONS must be SAMEORIGIN to allow iframe preview of media files "
        "(HU21 dual evidence rendering)."
    )


def test_production_settings_do_not_override_to_deny():
    """Production must inherit SAMEORIGIN from base, NOT override back to DENY,
    otherwise the iframe preview rota en producción.
    """
    prod = reload(import_module("config.settings.production"))
    assert prod.X_FRAME_OPTIONS == "SAMEORIGIN", (
        "production.py must not override X_FRAME_OPTIONS back to DENY — "
        "that would break HU21 preview in production."
    )


@pytest.mark.django_db
def test_response_header_is_sameorigin_not_deny():
    """Smoke: any Django response must carry X-Frame-Options: SAMEORIGIN."""
    client = Client()
    response = client.get("/")  # any view, the middleware adds the header globally
    header = response.get("X-Frame-Options", "")
    assert header.upper() == "SAMEORIGIN", (
        f"Expected SAMEORIGIN, got '{header}'. "
        "Django's XFrameOptionsMiddleware should pick up the setting."
    )
