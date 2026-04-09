"""
Email service for ECPPP.
Infrastructure layer — sends OTP and lockout notification emails.
Uses Django's email backend (console in dev, SMTP in prod).
"""

from django.conf import settings
from django.core.mail import send_mail


def send_otp_email(usuario, codigo: str) -> None:
    """
    Send OTP verification code to user's email.

    Args:
        usuario: Usuario model instance.
        codigo: 6-digit OTP code.
    """
    subject = "ECPPP — Código de verificación"
    message = (
        f"Hola {usuario.get_full_name() or usuario.username},\n\n"
        f"Su código de verificación es: {codigo}\n\n"
        f"Este código expira en {settings.OTP_EXPIRATION_MINUTES} minutos.\n"
        "Si no solicitó este código, ignore este mensaje.\n\n"
        "— Plataforma ECPPP"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )


def send_lockout_notification(usuario) -> None:
    """
    Notify user that their account has been locked due to failed login attempts.

    Args:
        usuario: Usuario model instance.
    """
    subject = "ECPPP — Cuenta bloqueada temporalmente"
    message = (
        f"Hola {usuario.get_full_name() or usuario.username},\n\n"
        f"Su cuenta ha sido bloqueada temporalmente debido a "
        f"{settings.MAX_LOGIN_ATTEMPTS} intentos fallidos de inicio de sesión.\n\n"
        f"Podrá intentar nuevamente en {settings.ACCOUNT_LOCKOUT_MINUTES} minutos.\n"
        "Si no fue usted, le recomendamos cambiar su contraseña.\n\n"
        "— Plataforma ECPPP"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=True,
    )
