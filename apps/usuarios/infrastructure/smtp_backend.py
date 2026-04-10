"""
Custom SMTP email backend for ECPPP.

Brevo routes South America traffic to offshore servers whose TLS certificate
CN (smtp-relay-offshore-southamerica-east-v2.sendinblue.com) does not match
the connection hostname (smtp-relay.brevo.com).  This backend disables
hostname checking while keeping certificate verification active.
"""

import ssl
from functools import cached_property

from django.core.mail.backends.smtp import EmailBackend


class BrevoEmailBackend(EmailBackend):
    """SMTP backend that skips hostname verification for Brevo STARTTLS."""

    @cached_property
    def ssl_context(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx
