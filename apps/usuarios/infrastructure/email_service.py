"""
Email service for ECPPP.
Infrastructure layer — sends OTP, lockout notification, and credential emails.
Uses HTML templates for professional presentation.
"""

from django.conf import settings

from apps.shared.email_utils import enviar_email_html


def send_otp_email(usuario, codigo: str) -> None:
    """
    Send OTP verification code to user's email.

    Args:
        usuario: Usuario model instance.
        codigo: 6-digit OTP code.
    """
    enviar_email_html(
        destinatario=usuario.email,
        asunto="ECPP — Código de verificación",
        template="emails/otp.html",
        contexto={
            "nombre": usuario.get_full_name() or usuario.username,
            "codigo": codigo,
            "expiracion_minutos": settings.OTP_EXPIRATION_MINUTES,
        },
        fail_silently=False,
    )


def send_credenciales_email(usuario, password_temporal: str) -> None:
    """
    Send temporary credentials to a newly created user.

    Args:
        usuario: Usuario model instance (already saved).
        password_temporal: Plain-text temporary password.
    """
    enviar_email_html(
        destinatario=usuario.email,
        asunto="ECPP — Credenciales de acceso a la plataforma",
        template="emails/credenciales.html",
        contexto={
            "nombre": usuario.get_full_name() or usuario.username,
            "email": usuario.email,
            "password_temporal": password_temporal,
        },
        fail_silently=False,
    )


def send_lockout_notification(usuario) -> None:
    """
    Notify user that their account has been locked due to failed login attempts.

    Args:
        usuario: Usuario model instance.
    """
    enviar_email_html(
        destinatario=usuario.email,
        asunto="ECPP — Cuenta bloqueada temporalmente",
        template="emails/lockout.html",
        contexto={
            "nombre": usuario.get_full_name() or usuario.username,
            "max_intentos": settings.MAX_LOGIN_ATTEMPTS,
            "lockout_minutos": settings.ACCOUNT_LOCKOUT_MINUTES,
        },
        fail_silently=True,
    )
