"""
Views for the Copilot bounded context (HU22).

Three JSON endpoints power the floating chat widget:
- POST /copilot/chat/            — send a user message, get a reply
- GET  /copilot/chat/            — fetch the active conversation history
- POST /copilot/nueva-conversacion/ — close current session, start a new one

Access is restricted to `estudiante` and `docente` via
`MultiRolRequeridoMixin`. The widget itself is rendered client-side
from the base template, so no HTML view is needed here.
"""

import json

from django.http import JsonResponse
from django.utils import timezone
from django.views import View

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import (
    MensajeDemaisiadoLargoError,
    MensajeVacioError,
    RateLimitExcedidoError,
    SesionLlenaError,
)
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin


class CopilotChatView(MultiRolRequeridoMixin, View):
    """API endpoint for copilot chat interactions."""

    roles_permitidos = ["estudiante", "docente"]
    MAX_LONGITUD_MENSAJE = 1000

    def get(self, request):
        """Return the active conversation history for the user."""
        service = CopilotAppService()
        conversacion_id, mensajes = service.obtener_historial(request.user)
        return JsonResponse(
            {
                "conversacion_id": conversacion_id,
                "mensajes": list(mensajes),
            }
        )

    def post(self, request):
        """Process a user message and return the assistant's reply."""
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido."}, status=400)

        mensaje = (body.get("mensaje") or "").strip()
        if not mensaje:
            return JsonResponse({"error": "El mensaje no puede estar vacío."}, status=400)
        if len(mensaje) > self.MAX_LONGITUD_MENSAJE:
            return JsonResponse(
                {
                    "error": (
                        f"El mensaje supera el límite de {self.MAX_LONGITUD_MENSAJE} caracteres."
                    )
                },
                status=400,
            )

        service = CopilotAppService()
        try:
            respuesta = service.procesar_mensaje(request.user, mensaje)
        except RateLimitExcedidoError as e:
            return JsonResponse(
                {
                    "error": (
                        f"Has excedido el límite de mensajes ({e.limite}/hora). "
                        "Intenta más tarde."
                    )
                },
                status=429,
            )
        except SesionLlenaError as e:
            return JsonResponse(
                {"error": f"Sesión llena ({e.maximo} mensajes). Inicia una nueva conversación."},
                status=400,
            )
        except (MensajeVacioError, MensajeDemaisiadoLargoError) as e:
            return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse(
            {
                "respuesta": respuesta,
                "timestamp": timezone.now().isoformat(),
            }
        )


class CopilotNuevaConversacionView(MultiRolRequeridoMixin, View):
    """Start a new conversation by closing the current one."""

    roles_permitidos = ["estudiante", "docente"]

    def post(self, request):
        service = CopilotAppService()
        nueva = service.cerrar_conversacion(request.user)
        return JsonResponse({"conversacion_id": str(nueva.id)})
