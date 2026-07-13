"""Signal receivers for the Copilot bounded context.

Resets the copilot conversation when the user logs out — either via a manual
logout or the inactivity timeout (HU31), both of which call
``django.contrib.auth.logout`` and therefore emit ``user_logged_out``. This
guarantees a fresh login always starts a new conversation, while the previous
messages remain in the database for auditing.
"""

from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from apps.copilot.infrastructure.models import ConversacionCopilot


@receiver(user_logged_out)
def cerrar_conversaciones_al_salir(sender, request, user, **kwargs):
    """Close the user's active copilot conversations on logout."""
    if user is None:
        return
    ConversacionCopilot.objects.filter(usuario=user, activa=True).update(activa=False)
