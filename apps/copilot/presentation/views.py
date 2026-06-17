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
import logging

from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.views import View

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import (
    ContenidoBloqueadoError,
    MensajeDemaisiadoLargoError,
    MensajeVacioError,
    RateLimitExcedidoError,
    SesionLlenaError,
)
from apps.copilot.domain.moderation import CANNED_REFUSAL
from apps.usuarios.presentation.permissions import MultiRolRequeridoMixin

logger = logging.getLogger(__name__)


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
        except ContenidoBloqueadoError:
            # PR 2 — cualquier rechazo de moderación (input STRONG, input
            # OpenAI-flagged, output OpenAI-flagged) retorna HTTP 200 con
            # ``CANNED_REFUSAL``. NO es un 4xx: para el cliente es una
            # respuesta exitosa del copilot con un mensaje de cortesía.
            return JsonResponse(
                {
                    "respuesta": CANNED_REFUSAL,
                    "timestamp": timezone.now().isoformat(),
                },
                status=200,
            )

        return JsonResponse(
            {
                "respuesta": respuesta,
                "timestamp": timezone.now().isoformat(),
            }
        )


class CopilotChatStreamView(MultiRolRequeridoMixin, View):
    """SSE endpoint — streams the assistant reply chunk by chunk."""

    roles_permitidos = ["estudiante", "docente"]
    MAX_LONGITUD_MENSAJE = 1000

    def post(self, request):
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
                        f"El mensaje supera el límite de {self.MAX_LONGITUD_MENSAJE} "
                        "caracteres."
                    ),
                },
                status=400,
            )

        service = CopilotAppService()
        try:
            stream = service.procesar_mensaje_stream(request.user, mensaje)
        except RateLimitExcedidoError as e:
            return JsonResponse(
                {
                    "error": (
                        f"Has excedido el límite de mensajes ({e.limite}/hora). "
                        "Intenta más tarde."
                    ),
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
        except ContenidoBloqueadoError:
            # PR 2 — input STRONG o OpenAI-flagged. Como el raise es
            # sincrónico (antes de que se cree el generator), no podemos
            # emitir un evento SSE: retornamos JSON 200 con la canned
            # refusal, igual que el endpoint bloqueante.
            return JsonResponse(
                {
                    "respuesta": CANNED_REFUSAL,
                    "timestamp": timezone.now().isoformat(),
                },
                status=200,
            )

        def sse_generator():
            # Comentario SSE de relleno: fuerza al browser a superar su buffer
            # inicial (~1 KB en Chrome) para que entregue los chunks de inmediato.
            yield ": " + ("x" * 1024) + "\n\n"
            try:
                for chunk in stream:
                    # PR 2 — el servicio puede emitir:
                    #   - ``str`` → delta de texto normal (forwarded al cliente).
                    #   - ``{"type": "replacement", "text": CANNED_REFUSAL}``
                    #     → cuando el hook D (primer chunk) o el hook B
                    #     (respuesta ensamblada) detectó contenido flagged
                    #     en la salida. El widget usa este evento para
                    #     sobrescribir el texto streameado.
                    if isinstance(chunk, dict) and chunk.get("type") == "replacement":
                        payload = json.dumps({"replacement": chunk["text"]}, ensure_ascii=False)
                    else:
                        payload = json.dumps({"delta": chunk}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            except Exception:
                logger.exception("Error durante el streaming SSE del copilot")
                yield f"data: {json.dumps({'error': 'Error generando la respuesta.'})}\n\n"
            yield "data: [DONE]\n\n"

        response = StreamingHttpResponse(
            sse_generator(),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class CopilotNuevaConversacionView(MultiRolRequeridoMixin, View):
    """Start a new conversation by closing the current one."""

    roles_permitidos = ["estudiante", "docente"]

    def post(self, request):
        service = CopilotAppService()
        nueva = service.cerrar_conversacion(request.user)
        return JsonResponse({"conversacion_id": str(nueva.id)})
