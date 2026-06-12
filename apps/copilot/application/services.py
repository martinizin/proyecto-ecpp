"""Application service (use case) for the Copilot bounded context.

Orchestrates: session lifecycle, message persistence, rate limiting,
query classification, academic data fetch, and the call to OpenAI.
"""

from __future__ import annotations

from collections import Counter, defaultdict
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


class AcademicDataService:
    """Queries actual DB data to build academic context for the copilot.

    Each ``obtener_datos(tipo)`` method returns a Markdown-formatted string
    that gets injected into the system prompt so the LLM can answer with
    real user data.
    """

    def obtener_datos(self, usuario, tipo: str) -> str:
        """Return formatted academic data for the given user and query type."""
        if tipo == "calificaciones":
            return self._obtener_calificaciones(usuario)
        elif tipo == "solicitudes":
            return self._obtener_solicitudes(usuario)
        elif tipo == "asistencia":
            return self._obtener_asistencia(usuario)
        elif tipo == "horario":
            return self._obtener_horario(usuario)
        elif tipo in ("informacion", "general"):
            return self._obtener_informacion(usuario)
        return "No hay datos disponibles para esta consulta."

    # ------------------------------------------------------------------ #
    # Calificaciones
    # ------------------------------------------------------------------ #
    def _obtener_calificaciones(self, usuario) -> str:
        from apps.calificaciones.infrastructure.models import Calificacion

        qs = (
            Calificacion.objects.filter(estudiante=usuario)
            .select_related("evaluacion__paralelo__asignatura")
            .order_by("evaluacion__paralelo__asignatura__codigo", "evaluacion__tipo")
        )
        if not qs.exists():
            return "No hay calificaciones registradas para este usuario."

        lines: list[str] = []
        current_asig: str | None = None
        for c in qs:
            asig = (
                f"{c.evaluacion.paralelo.asignatura.codigo} — "
                f"{c.evaluacion.paralelo.asignatura.nombre}"
            )
            if asig != current_asig:
                lines.append(f"\n### {asig}")
                current_asig = asig
            lines.append(
                f"- {c.evaluacion.get_tipo_display()}: {c.nota}/20"
                f"{' — ' + c.observaciones if c.observaciones else ''}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Solicitudes (rectificaciones + justificaciones)
    # ------------------------------------------------------------------ #
    def _obtener_solicitudes(self, usuario) -> str:
        from apps.solicitudes.infrastructure.models import Solicitud

        qs = (
            Solicitud.objects.filter(estudiante=usuario)
            .select_related("asistencia__paralelo__asignatura", "calificacion__evaluacion__paralelo__asignatura")
            .order_by("-fecha_creacion")[:10]
        )

        if not qs.exists():
            return "No hay solicitudes registradas para este usuario."

        lines = ["Últimas solicitudes:"]
        for s in qs:
            referencia = ""
            if s.tipo == "justificacion" and s.asistencia:
                a = s.asistencia
                referencia = (
                    f" · Inasistencia del {a.fecha:%d/%m/%Y}"
                    f" en {a.paralelo.asignatura.codigo}"
                )
            elif s.tipo == "rectificacion" and s.calificacion:
                c = s.calificacion
                referencia = (
                    f" · {c.evaluacion.paralelo.asignatura.codigo}"
                    f" — {c.evaluacion.get_tipo_display()}"
                )
            estado = s.get_estado_display()
            resolucion = f" (resuelta {s.fecha_resolucion:%d/%m/%Y})" if s.fecha_resolucion else ""
            lines.append(
                f"- [{s.get_tipo_display()}] {estado}{resolucion} — "
                f"creada {s.fecha_creacion:%d/%m/%Y}{referencia}\n"
                f"  Motivo: {s.descripcion[:200]}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Asistencia
    # ------------------------------------------------------------------ #
    def _obtener_asistencia(self, usuario) -> str:
        from apps.asistencia.infrastructure.models import Asistencia

        qs = (
            Asistencia.objects.filter(estudiante=usuario)
            .select_related("paralelo__asignatura")
            .prefetch_related("solicitudes_justificacion")
            .order_by("paralelo__asignatura__codigo", "fecha")
        )
        if not qs.exists():
            return "No hay registros de asistencia para este usuario."

        por_asig: dict[str, list] = defaultdict(list)
        for a in qs:
            key = f"{a.paralelo.asignatura.codigo} — {a.paralelo.asignatura.nombre}"
            por_asig[key].append(a)

        lines: list[str] = []
        for asig, registros in por_asig.items():
            total = len(registros)
            conteo = Counter(r.estado for r in registros)
            presentes = conteo.get("presente", 0)
            ausentes = conteo.get("ausente", 0)
            justificados = conteo.get("justificado", 0)
            pct = round(presentes / total * 100, 1) if total else 0

            lines.append(f"\n### {asig}")
            lines.append(
                f"Asistencia general: {presentes}/{total} clases ({pct}%)"
                + (f" · {ausentes} ausencia(s)" if ausentes else "")
                + (f" · {justificados} justificada(s)" if justificados else "")
            )

            inasistencias = [r for r in registros if r.estado != "presente"]
            if inasistencias:
                lines.append("Fechas de inasistencia:")
                for r in inasistencias:
                    sol = r.solicitudes_justificacion.first()
                    if r.estado == "justificado":
                        detalle = "Justificada"
                        if sol:
                            detalle += f" (solicitud {sol.get_estado_display().lower()})"
                    elif sol:
                        detalle = f"Sin justificar · solicitud {sol.get_estado_display().lower()}"
                    else:
                        detalle = "Sin justificar · sin solicitud"
                    lines.append(f"- {r.fecha:%d/%m/%Y}: {detalle}")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Horario
    # ------------------------------------------------------------------ #
    def _obtener_horario(self, usuario) -> str:
        from apps.academico.infrastructure.models import Matricula

        matriculas = (
            Matricula.objects.filter(estudiante=usuario, estado="activa")
            .select_related("paralelo__asignatura", "paralelo__docente")
            .prefetch_related("paralelo__bloques_horario")
        )
        if not matriculas.exists():
            return "No tienes paralelos activos este período."

        DIA_ORDEN = {
            "lunes": 1, "martes": 2, "miercoles": 3,
            "jueves": 4, "viernes": 5, "sabado": 6,
        }
        lines: list[str] = []
        for m in matriculas:
            p = m.paralelo
            lines.append(f"\n### {p.asignatura.codigo} — {p.asignatura.nombre}")
            if p.docente:
                lines.append(f"Docente: {p.docente.get_full_name()}")
            lines.append(f"Paralelo: {p.nombre}")
            bloques = list(p.bloques_horario.all())
            bloques.sort(key=lambda b: (DIA_ORDEN.get(b.dia_semana, 99), b.hora_inicio))
            for b in bloques:
                lines.append(
                    f"- {b.get_dia_semana_display()} {b.hora_inicio:%H:%M}–{b.hora_fin:%H:%M}"
                )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Información general del usuario
    # ------------------------------------------------------------------ #
    def _obtener_informacion(self, usuario) -> str:
        from apps.academico.infrastructure.models import Matricula

        rol = getattr(usuario, "rol", "desconocido")
        info = [f"Rol: {rol}", f"Nombre: {usuario.get_full_name()}"]

        if rol == "estudiante":
            matriculas = (
                Matricula.objects.filter(estudiante=usuario, estado="activa")
                .select_related(
                    "paralelo__asignatura",
                    "paralelo__periodo__tipo_licencia",
                    "paralelo__docente",
                )
            )
            if matriculas.exists():
                info.append("\n### Matrícula activa")
                for m in matriculas:
                    p = m.paralelo
                    info.append(f"- {p.asignatura.codigo} — {p.asignatura.nombre}")
                    info.append(f"  Paralelo: {p.nombre}")
                    info.append(
                        f"  Periodo: {p.periodo.nombre} ({p.periodo.tipo_licencia.codigo})"
                    )
                    if p.docente:
                        info.append(f"  Docente: {p.docente.get_full_name()}")
            else:
                info.append("\nSin matrícula activa este período.")
        elif rol == "docente":
            paralelos = usuario.paralelos_asignados.select_related(
                "asignatura", "periodo__tipo_licencia",
            ).all()
            if paralelos.exists():
                info.append("\n### Paralelos asignados")
                for p in paralelos:
                    info.append(
                        f"- {p.asignatura.codigo} — {p.asignatura.nombre} "
                        f"({p.nombre}) — {p.periodo.nombre}"
                    )
            else:
                info.append("\nSin paralelos asignados.")

        return "\n".join(info)


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
        self.academic_data_service = academic_data_service or AcademicDataService()

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
        return (
            "Eres un asistente académico de la ECPPP "
            "(Escuela de Capacitación de Conductores Profesionales).\n\n"
            "## Datos del usuario\n"
            f"{datos_academicos}\n\n"
            "## Reglas\n"
            "- Responde SOLO con información del usuario autenticado que se te ha proporcionado.\n"
            "- NO puedes modificar datos del sistema, solo consultar.\n"
            "- Responde SIEMPRE en español, de forma clara, concisa y amable.\n"
            "- Si el usuario pregunta sobre algo que no está en los datos, indícalo claramente.\n"
            "- No inventes datos ni asumas información que no esté en el contexto.\n"
            "- Para solicitudes/reclamos: indica el estado actual pero deriva al usuario a "
            "secretaría para gestiones que requieran acción.\n"
            "- Para calificaciones: muestra las notas pero no hagas cálculos que no estén "
            "explícitos en los datos.\n"
        )
