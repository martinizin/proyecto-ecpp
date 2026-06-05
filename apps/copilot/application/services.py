"""Application service (use case) for the Copilot bounded context.

Orchestrates: session lifecycle, message persistence, rate limiting,
query classification, academic data fetch, and the call to OpenAI.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from django.utils import timezone

from apps.copilot.domain.exceptions import (
    RateLimitExcedidoError,
    SesionLlenaError,
)
from apps.copilot.domain.services import QueryClassifierService
from apps.copilot.infrastructure.models import (
    ConversacionCopilot,
    MensajeCopilot,
)
from apps.copilot.infrastructure.openai_client import OpenAIClient


class AcademicDataServiceProtocol(Protocol):
    """Protocol that the AcademicDataService must implement.

    The real implementation lives in the academic / asistencia /
    calificaciones apps and is injected into CopilotAppService.
    """

    def obtener_datos(self, usuario, tipo: str) -> str: ...


class AcademicDataServiceStub:
    """Temporary stub implementation.

    Returns a deterministic placeholder string so the copilot can run
    end-to-end during HU22. HU24 will replace this via DI with the real
    service that joins calificaciones / asistencia / horario data.
    """

    def obtener_datos(self, usuario, tipo: str) -> str:
        return (
            f"[Datos académicos del usuario {getattr(usuario, 'username', usuario)} "
            f"para la consulta tipo '{tipo}' no están disponibles en esta versión.]"
        )


class CopilotAppService:
    """Use case orchestrator for copilot chat interactions."""

    MAX_MENSAJES_POR_SESION = 50
    MAX_MENSAJES_POR_HORA = 30
    SESION_TIMEOUT_HORAS = 24
    MAX_TOKENS_RESPUESTA = 500

    def __init__(
        self,
        openai_client: OpenAIClient | None = None,
        academic_data_service: AcademicDataServiceProtocol | None = None,
    ):
        self.openai_client = openai_client or OpenAIClient()
        self.academic_data_service = academic_data_service or AcademicDataServiceStub()

    # ------------------------------------------------------------------ #
    # Sesión
    # ------------------------------------------------------------------ #
    def obtener_o_crear_conversacion(self, usuario) -> ConversacionCopilot:
        """Return the active session for the user or create a new one."""
        timeout = timezone.now() - timedelta(hours=self.SESION_TIMEOUT_HORAS)
        conversacion = ConversacionCopilot.objects.filter(
            usuario=usuario,
            activa=True,
            ultima_actividad__gte=timeout,
        ).first()
        if conversacion is None:
            conversacion = ConversacionCopilot.objects.create(usuario=usuario)
        return conversacion

    def cerrar_conversacion(self, usuario) -> ConversacionCopilot:
        """Close any active session for the user and create a new empty one."""
        ConversacionCopilot.objects.filter(usuario=usuario, activa=True).update(activa=False)
        return ConversacionCopilot.objects.create(usuario=usuario)

    # ------------------------------------------------------------------ #
    # Rate limit
    # ------------------------------------------------------------------ #
    def _excede_rate_limit(self, usuario) -> bool:
        una_hora_atras = timezone.now() - timedelta(hours=1)
        return (
            MensajeCopilot.objects.filter(
                conversacion__usuario=usuario,
                rol=MensajeCopilot.Rol.USER,
                timestamp__gte=una_hora_atras,
            ).count()
            >= self.MAX_MENSAJES_POR_HORA
        )

    # ------------------------------------------------------------------ #
    # Mensaje
    # ------------------------------------------------------------------ #
    def procesar_mensaje(self, usuario, contenido: str) -> str:
        """Process a user message end-to-end and return the assistant's reply."""
        if self._excede_rate_limit(usuario):
            raise RateLimitExcedidoError(limite=self.MAX_MENSAJES_POR_HORA)

        conversacion = self.obtener_o_crear_conversacion(usuario)

        msg_count = conversacion.mensajes.count()
        if msg_count >= self.MAX_MENSAJES_POR_SESION:
            raise SesionLlenaError(maximo=self.MAX_MENSAJES_POR_SESION)

        # Guardar mensaje del usuario
        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.USER,
            contenido=contenido,
        )

        # Clasificar y traer datos académicos
        consulta = QueryClassifierService.clasificar(contenido)
        datos_academicos = self.academic_data_service.obtener_datos(
            usuario=usuario, tipo=consulta.tipo
        )

        # Construir system prompt
        system_prompt = self._construir_system_prompt(usuario, datos_academicos)

        # Historial reciente
        historial = list(
            conversacion.mensajes.order_by("timestamp").values("rol", "contenido")[:20]
        )

        # Llamar a OpenAI
        respuesta, tokens = self.openai_client.chat_completion(
            system_prompt=system_prompt,
            messages=historial,
            max_tokens=self.MAX_TOKENS_RESPUESTA,
        )

        # Guardar respuesta del asistente
        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.ASSISTANT,
            contenido=respuesta,
            tokens_usados=tokens,
        )

        # Refrescar ultima_actividad
        conversacion.save(update_fields=["ultima_actividad"])

        return respuesta

    def obtener_historial(self, usuario) -> tuple[str, list[dict]]:
        """Return the active conversation id and its messages."""
        conversacion = self.obtener_o_crear_conversacion(usuario)
        mensajes = list(
            conversacion.mensajes.order_by("timestamp").values("rol", "contenido", "timestamp")
        )
        return str(conversacion.id), mensajes

    # ------------------------------------------------------------------ #
    # System prompt
    # ------------------------------------------------------------------ #
    def _construir_system_prompt(self, usuario, datos_academicos: str) -> str:
        rol = getattr(usuario, "rol", "desconocido")
        return (
            "Eres el asistente académico de la ECPPP (Escuela de Capacitación de Policía).\n"
            f"Rol del usuario: {rol}\n"
            "Datos académicos del usuario:\n"
            f"{datos_academicos}\n\n"
            "Reglas:\n"
            "- Responde SOLO con información del usuario autenticado.\n"
            "- NO puedes modificar datos, solo consultar.\n"
            "- Responde en español, de forma concisa y amable.\n"
            "- Si no tienes la información, indícalo claramente.\n"
            "- No inventes datos.\n"
        )
