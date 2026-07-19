"""
Custom SMTP email backend for ECPPP.

Brevo routes South America traffic to offshore relay servers whose TLS
certificate is issued for *.sendinblue.com names (Brevo's former brand)
and does not include smtp-relay.brevo.com in its SAN.  Instead of
disabling hostname verification, this backend keeps full certificate and
hostname verification enabled and validates the certificate against the
legacy Sendinblue hostname, which Brevo includes in every relay
certificate (verified against the offshore South America relay).
"""

import ssl
from functools import cached_property

from django.core.mail.backends.smtp import EmailBackend

# Hostname present in the SAN of Brevo relay certificates, including the
# offshore South America relays that back smtp-relay.brevo.com.
BREVO_TLS_HOSTNAME = "smtp-relay.sendinblue.com"


class BrevoEmailBackend(EmailBackend):
    """SMTP backend with TLS verification pinned to Brevo's certificate hostname."""

    @cached_property
    def ssl_context(self):
        ctx = ssl.create_default_context()
        default_wrap_socket = ctx.wrap_socket

        def wrap_socket(sock, **kwargs):
            # smtplib passes server_hostname=EMAIL_HOST; override it so the
            # certificate is checked against the name Brevo actually serves.
            kwargs["server_hostname"] = BREVO_TLS_HOSTNAME
            return default_wrap_socket(sock, **kwargs)

        ctx.wrap_socket = wrap_socket
        return ctx
