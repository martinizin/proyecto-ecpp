"""
Tests for BrevoEmailBackend TLS configuration (SonarCloud S5527).

The backend must keep full certificate and hostname verification enabled,
pinning the verified hostname to the Sendinblue name Brevo serves in the
SAN of its offshore South America relay certificates.
"""

import ssl
from unittest import mock

from apps.usuarios.infrastructure.smtp_backend import (
    BREVO_TLS_HOSTNAME,
    BrevoEmailBackend,
)


def test_ssl_context_keeps_full_verification():
    """check_hostname stays enabled and certificates are required."""
    backend = BrevoEmailBackend()
    ctx = backend.ssl_context

    assert ctx.check_hostname is True
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_wrap_socket_pins_certificate_hostname():
    """server_hostname passed by smtplib is overridden with the Brevo SAN name."""
    backend = BrevoEmailBackend()
    with mock.patch.object(ssl.SSLContext, "wrap_socket") as default_wrap:
        ctx = backend.ssl_context
        sock = object()
        result = ctx.wrap_socket(sock, server_hostname="smtp-relay.brevo.com")

    default_wrap.assert_called_once_with(sock, server_hostname=BREVO_TLS_HOSTNAME)
    assert result is default_wrap.return_value


def test_ssl_context_is_cached():
    """The context is built once per backend instance (cached_property)."""
    backend = BrevoEmailBackend()
    assert backend.ssl_context is backend.ssl_context
