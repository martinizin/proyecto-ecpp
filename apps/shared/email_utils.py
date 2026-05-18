"""
Shared email rendering utility.
Renders HTML email templates with base context (logo_url) and sends both
HTML and plain-text fallback.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def enviar_email_html(
    destinatario: str | list[str],
    asunto: str,
    template: str,
    contexto: dict,
    fail_silently: bool = True,
) -> None:
    """
    Render an HTML email template and send it.

    Args:
        destinatario: Email address or list of addresses.
        asunto: Email subject line.
        template: Template path relative to templates/ (e.g. 'emails/otp.html').
        contexto: Context dict for the template (logo_url is injected automatically).
        fail_silently: Whether to suppress send errors.
    """
    if isinstance(destinatario, str):
        destinatario = [destinatario]

    # Inject shared context
    contexto.setdefault("logo_url", getattr(settings, "LOGO_URL", ""))

    html_message = render_to_string(template, contexto)

    # Plain-text fallback: strip tags roughly
    from django.utils.html import strip_tags

    text_message = strip_tags(html_message)

    send_mail(
        subject=asunto,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatario,
        html_message=html_message,
        fail_silently=fail_silently,
    )
