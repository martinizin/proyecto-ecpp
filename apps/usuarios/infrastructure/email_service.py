"""
Email service for ECPPP.
Infrastructure layer — sends OTP, lockout notification, and credential emails.
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


def send_credenciales_email(usuario, password_temporal: str) -> None:
    """
    Send temporary credentials to a newly created user.
    Called by Django Admin when the secretariat creates a user account.

    Args:
        usuario: Usuario model instance (already saved).
        password_temporal: Plain-text temporary password.
    """
    subject = "ECPPP — Credenciales de acceso a la plataforma"
    message = (
        f"Hola {usuario.get_full_name() or usuario.username},\n\n"
        "Se le ha creado una cuenta en la Plataforma Académica ECPPP.\n\n"
        "Sus credenciales de acceso son:\n"
        f"  Correo electrónico: {usuario.email}\n"
        f"  Contraseña temporal: {password_temporal}\n\n"
        "IMPORTANTE: Al iniciar sesión por primera vez, el sistema le solicitará "
        "cambiar su contraseña por una nueva.\n\n"
        "Acceda a la plataforma desde el enlace proporcionado por la institución.\n\n"
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
