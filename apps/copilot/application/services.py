"""Application service (use case) for the Copilot bounded context.

Orchestrates: session lifecycle, message persistence, rate limiting,
query classification, academic data fetch, content moderation (input +
output), and the call to OpenAI.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Protocol

import openai
from django.utils import timezone

from apps.copilot.domain.exceptions import (
    ContenidoBloqueadoError,
    RateLimitExcedidoError,
    SesionLlenaError,
)
from apps.copilot.domain.moderation import CANNED_REFUSAL
from apps.copilot.domain.services import QueryClassifierService
from apps.copilot.infrastructure.models import (
    ConversacionCopilot,
    MensajeCopilot,
)
from apps.copilot.infrastructure.openai_client import OpenAIClient


logger = logging.getLogger("apps.copilot.moderation")


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
        elif tipo == "navegacion":
            return self._obtener_navegacion(usuario)
        return "No hay datos disponibles para esta consulta."

    # ------------------------------------------------------------------ #
    # Calificaciones
    # ------------------------------------------------------------------ #
    def _obtener_calificaciones(self, usuario) -> str:
        from apps.calificaciones.application.services import LibretaCalificacionesAppService

        libreta = LibretaCalificacionesAppService.obtener_libreta(usuario)
        materias = libreta.get("materias", [])

        if not materias:
            return "No hay calificaciones registradas para este usuario."

        lines: list[str] = []

        for materia in materias:
            paralelo = materia["paralelo"]
            asig = paralelo.asignatura
            lines.append(f"\n### {asig.codigo} — {asig.nombre}")

            if not materia["notas_visibles"]:
                lines.append("_(Notas aún no publicadas por el docente)_")
                continue

            for ev in materia["evaluaciones"]:
                nota_str = f"{ev['nota']}/20" if ev["nota"] is not None else "—"
                lines.append(f"- {ev['tipo']} ({ev['peso']}%): {nota_str}")

            if materia["promedio"] is not None:
                lines.append(f"**Promedio ponderado: {materia['promedio']}/20**")

        promedio_general = libreta.get("promedio_general")
        if promedio_general is not None:
            lines.append(f"\n---\n**Promedio general: {promedio_general}/20**")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Solicitudes (rectificaciones + justificaciones)
    # ------------------------------------------------------------------ #
    def _obtener_solicitudes(self, usuario) -> str:
        from apps.solicitudes.infrastructure.models import Solicitud

        qs = (
            Solicitud.objects.filter(estudiante=usuario)
            .select_related(
                "asistencia__paralelo__asignatura",
                "calificacion__evaluacion__paralelo__asignatura",
            )
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
                    f" · Inasistencia del {a.fecha:%d/%m/%Y}" f" en {a.paralelo.asignatura.codigo}"
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
            "lunes": 1,
            "martes": 2,
            "miercoles": 3,
            "jueves": 4,
            "viernes": 5,
            "sabado": 6,
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
    # Navegación — instrucciones de uso del sistema por rol
    # ------------------------------------------------------------------ #
    def _obtener_navegacion(self, usuario) -> str:
        rol = getattr(usuario, "rol", "desconocido")

        guia_comun = """
### Acciones disponibles en la plataforma para todos los usuarios

**Cambiar contraseña**
1. En el menú lateral izquierdo, hacé clic en **Mi Perfil** (sección "Mi Cuenta").
2. En la página de perfil, seleccioná el botón **Cambiar Contraseña**.
3. Completá los campos: contraseña actual, nueva contraseña y confirmación.
4. Hacé clic en **Guardar** para aplicar el cambio.

**Ver tu perfil**
1. En el menú lateral izquierdo, hacé clic en **Mi Perfil** (sección "Mi Cuenta").
2. Verás tu información personal registrada en la plataforma.

**Recuperar contraseña olvidada**
1. En la pantalla de inicio de sesión, hacé clic en **¿Olvidaste tu contraseña?**
2. Ingresá tu correo electrónico institucional registrado.
3. Revisá tu correo: recibirás un enlace para restablecer la contraseña.
4. Hacé clic en el enlace y establecé una nueva contraseña."""

        if rol == "estudiante":
            return (
                guia_comun
                + """

### Acciones específicas para estudiantes

**Ver mis calificaciones (Mi Libreta)**
1. En el menú lateral izquierdo, hacé clic en **Mi Libreta**.
2. Verás todas tus notas organizadas por asignatura y tipo de evaluación.

**Ver mi asistencia**
1. En el menú lateral izquierdo, hacé clic en **Mi Asistencia**.
2. Verás el porcentaje de asistencia, las ausencias y el estado de justificaciones por materia.

**Ver mi horario de clases**
1. En el menú lateral izquierdo, hacé clic en **Mi Horario**.
2. Verás los días y franjas horarias de cada asignatura en la que estás matriculado.

**Justificar una inasistencia desde la plataforma**
1. En el menú lateral izquierdo, hacé clic en **Justificación** (sección Solicitudes).
2. Se mostrará la lista de tus inasistencias pendientes de justificar.
3. Seleccioná la inasistencia que querés justificar.
4. Adjuntá el certificado o documento de respaldo (médico, laboral, etc.).
5. Hacé clic en **Enviar solicitud**.
6. Podés revisar el estado de la solicitud en **Mis Solicitudes**.

**Solicitar recalificación de una nota**
1. En el menú lateral izquierdo, hacé clic en **Recalificación** (sección Solicitudes).
2. Seleccioná la asignatura y la evaluación cuya nota querés impugnar.
3. Escribí el motivo de la solicitud en el campo correspondiente.
4. Hacé clic en **Enviar solicitud**.
5. Podés revisar el estado en **Mis Solicitudes**.

**Ver el estado de mis solicitudes**
1. En el menú lateral izquierdo, hacé clic en **Mis Solicitudes**.
2. Verás el listado de todas tus solicitudes con su estado (pendiente, aprobada, rechazada) y la fecha de resolución."""
            )

        elif rol == "docente":
            return (
                guia_comun
                + """

### Acciones específicas para docentes

**Registrar asistencia de un paralelo**
1. En el menú lateral izquierdo, hacé clic en **Registro de Asistencia**.
2. Seleccioná el paralelo para el que querés registrar asistencia.
3. Marcá el estado de cada estudiante (presente, ausente) y hacé clic en **Guardar**.

**Registrar calificaciones**
1. En el menú lateral izquierdo, hacé clic en **Registro de Calificaciones**.
2. Seleccioná el paralelo correspondiente.
3. Elegí la evaluación, ingresá las notas de cada estudiante y hacé clic en **Guardar**.

**Ver mi horario de clases**
1. En el menú lateral izquierdo, hacé clic en **Mi Horario**.
2. Verás los horarios de todos los paralelos que tenés asignados.

**Gestionar solicitudes de recalificación**
1. En el menú lateral izquierdo, hacé clic en **Solicitudes Pendientes**.
2. Verás las solicitudes de recalificación enviadas por tus estudiantes.
3. Revisá cada solicitud y seleccioná **Aprobar** o **Rechazar** con tu justificación."""
            )

        return guia_comun + f"\n\nNota: guía de navegación no disponible para el rol '{rol}'."

    # ------------------------------------------------------------------ #
    # Información general del usuario
    # ------------------------------------------------------------------ #
    def _obtener_informacion(self, usuario) -> str:
        from apps.academico.infrastructure.models import Matricula

        rol = getattr(usuario, "rol", "desconocido")
        info = [f"Rol: {rol}", f"Nombre: {usuario.get_full_name()}"]

        if rol == "estudiante":
            matriculas = Matricula.objects.filter(
                estudiante=usuario, estado="activa"
            ).select_related(
                "paralelo__asignatura",
                "paralelo__periodo__tipo_licencia",
                "paralelo__docente",
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
                "asignatura",
                "periodo__tipo_licencia",
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
        moderation_service=None,
    ):
        self.openai_client = openai_client or OpenAIClient()
        self.academic_data_service = academic_data_service or AcademicDataService()
        # El ``moderation_service`` opcional permite a los tests inyectar un
        # ``ModeracionServicio`` con providers fakeados. La producción usa
        # ``_build_default_moderation_service()`` que cablea los providers de
        # PR 1b (``HardcodedWordListProvider`` + ``OpenAIModerationClient``)
        # leyendo la configuración de Django.
        if moderation_service is None:
            moderation_service = self._build_default_moderation_service()
        self.moderation_service = moderation_service

    @staticmethod
    def _build_default_moderation_service():
        """Construye un ``ModeracionServicio`` de producción con los providers
        de PR 1b y la configuración de Django.

        Importaciones diferidas para evitar acoplar el módulo a Django
        settings al momento de import (tests con ``settings`` no inicializado).
        """
        from django.conf import settings

        from apps.copilot.data.palabras_censuradas import (
            DEFAULT_PROFANITY_LIGHT,
            DEFAULT_PROFANITY_STRONG,
        )
        from apps.copilot.domain.moderation import ModeracionServicio
        from apps.copilot.infrastructure.hardcoded_wordlist import (
            HardcodedWordListProvider,
        )
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        provider_lista = HardcodedWordListProvider(
            lista_light=list(DEFAULT_PROFANITY_LIGHT),
            lista_strong=list(DEFAULT_PROFANITY_STRONG),
            allowlist=HardcodedWordListProvider.cargar_allowlist_desde_json(
                settings.COPILOT_MODERATION_ALLOWLIST_PATH
            ),
        )
        provider_openai = OpenAIModerationClient()
        return ModeracionServicio(
            proveedor_lista_dura=provider_lista,
            proveedor_moderacion_externo=provider_openai,
            habilitado=settings.COPILOT_MODERATION_ENABLED,
        )

    # ------------------------------------------------------------------ #
    # Moderación de salida (helper de orquestación)
    # ------------------------------------------------------------------ #
    def _moderar_salida(self, texto: str) -> str:
        """Aplica la moderación de salida sobre el texto del LLM.

        Comportamiento:
            - Si el feature flag está apagado: retorna el texto sin tocar.
            - Si el provider externo lanza ``openai.APIError`` (REQ-009): fail-SKIP
              en salida — retorna el texto del LLM sin modificar y loggea ERROR.
            - Si la API responde ``flagged=True``: levanta
              ``ContenidoBloqueadoError(razon="openai_output")``.
            - Caso contrario: retorna el texto tal cual.

        El servicio de dominio (``ModeracionServicio``) sólo expone
        ``evaluar_input`` + ``sanitizar`` (PR 1a); el check de salida lo
        hace el orquestador de aplicación directamente sobre el provider
        para no contaminar la capa de dominio con dependencias de streaming.
        """
        if not self.moderation_service._habilitado:
            return texto
        try:
            flagged = self.moderation_service._proveedor_externo.clasificar(texto)
        except openai.APIError as exc:
            # REQ-009 — fail-SKIP en output: la respuesta del LLM se devuelve
            # tal cual y se loggea ERROR con la categoría de error.
            logger.error(
                "copilot.moderation.api.error",
                extra={
                    "fase": "output",
                    "error_class": type(exc).__name__,
                },
            )
            return texto
        if flagged:
            raise ContenidoBloqueadoError(razon="openai_output")
        return texto

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
    def procesar_mensaje(self, usuario, contenido: str, *, request_id: str = "") -> str:
        """Process a user message end-to-end and return the assistant's reply."""
        if self._excede_rate_limit(usuario):
            raise RateLimitExcedidoError(limite=self.MAX_MENSAJES_POR_HORA)

        conversacion = self.obtener_o_crear_conversacion(usuario)

        msg_count = conversacion.mensajes.count()
        if msg_count >= self.MAX_MENSAJES_POR_SESION:
            raise SesionLlenaError(maximo=self.MAX_MENSAJES_POR_SESION)

        # ---- Moderación de entrada (PR 2) ---------------------------------
        # El ``evaluar_input`` puede levantar ``ContenidoBloqueadoError``
        # (Tier 3a/3b) ANTES de que se cree la fila del user, NO se llame al
        # LLM y NO se consuman créditos. Para CLEAN/LIGHT retorna un
        # ``ResultadoModeracion`` que ``sanitizar`` traduce al texto que se
        # debe enviar al LLM / persistir (censurado para LIGHT, original
        # para CLEAN).
        if not request_id:
            request_id = uuid.uuid4().hex
        resultado_input = self.moderation_service.evaluar_input(contenido, request_id=request_id)
        contenido_a_persistir_y_llm = self.moderation_service.sanitizar(contenido, resultado_input)

        # Guardar mensaje del usuario (versión censurada para LIGHT; original
        # para CLEAN). El ``sanitizar`` ya garantiza que para STRONG no
        # llegamos aquí (la excepción burbujea desde ``evaluar_input``).
        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.USER,
            contenido=contenido_a_persistir_y_llm,
        )

        # Clasificar y traer datos académicos
        consulta = QueryClassifierService.clasificar(contenido_a_persistir_y_llm)
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

        # ---- Moderación de salida (PR 2) ----------------------------------
        # Si la respuesta del LLM es flagged: persistimos CANNED_REFUSAL
        # (NO la respuesta cruda) y retornamos CANNED_REFUSAL. Si está
        # clean: persistimos y retornamos la respuesta del LLM.
        try:
            respuesta_final = self._moderar_salida(respuesta)
        except ContenidoBloqueadoError:
            respuesta_final = CANNED_REFUSAL

        # Guardar respuesta del asistente
        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.ASSISTANT,
            contenido=respuesta_final,
            tokens_usados=tokens,
        )

        # Refrescar ultima_actividad
        conversacion.save(update_fields=["ultima_actividad"])

        return respuesta_final

    def procesar_mensaje_stream(self, usuario, contenido: str, *, request_id: str = ""):
        """Validate, persist, and return a generator that streams OpenAI deltas.

        Unlike ``procesar_mensaje``, this is a regular function (not a
        generator), so domain exceptions are raised synchronously. The returned
        generator yields text chunks and saves the assembled response to the DB
        once all chunks have been consumed.

        El generador retornado emite:
            - ``str`` (un chunk de texto) — forwarded al cliente como ``delta``.
            - ``{"type": "replacement", "text": CANNED_REFUSAL}`` — cuando el
              hook D (primer chunk) o el hook B (respuesta ensamblada) detecta
              contenido flagged. La vista traduce este marker a un evento SSE
              ``replacement`` (PR 2, design §B+D hooks).
        """
        if self._excede_rate_limit(usuario):
            raise RateLimitExcedidoError(limite=self.MAX_MENSAJES_POR_HORA)

        conversacion = self.obtener_o_crear_conversacion(usuario)

        msg_count = conversacion.mensajes.count()
        if msg_count >= self.MAX_MENSAJES_POR_SESION:
            raise SesionLlenaError(maximo=self.MAX_MENSAJES_POR_SESION)

        # ---- Moderación de entrada (PR 2) — mismo path que blocking -------
        # El ``evaluar_input`` puede levantar ``ContenidoBloqueadoError``
        # (Tier 3a/3b) ANTES de retornar el generator. La vista captura la
        # excepción sincrónicamente y devuelve JSON 200 con CANNED_REFUSAL.
        if not request_id:
            request_id = uuid.uuid4().hex
        resultado_input = self.moderation_service.evaluar_input(contenido, request_id=request_id)
        contenido_a_persistir_y_llm = self.moderation_service.sanitizar(contenido, resultado_input)

        MensajeCopilot.objects.create(
            conversacion=conversacion,
            rol=MensajeCopilot.Rol.USER,
            contenido=contenido_a_persistir_y_llm,
        )

        consulta = QueryClassifierService.clasificar(contenido_a_persistir_y_llm)
        datos_academicos = self.academic_data_service.obtener_datos(
            usuario=usuario, tipo=consulta.tipo
        )
        system_prompt = self._construir_system_prompt(usuario, datos_academicos)
        historial = list(
            conversacion.mensajes.order_by("timestamp").values("rol", "contenido")[:20]
        )

        return self._stream_openai(conversacion, system_prompt, historial)

    def _stream_openai(self, conversacion, system_prompt: str, historial: list[dict]):
        """Generator: yield text deltas from OpenAI, save full reply when done.

        PR 2 — implementa los hooks B (post-stream) y D (first-chunk) de
        moderación de salida (design §B+D hooks). El generador puede emitir:
            - ``str`` — un delta del LLM (forwarded al cliente).
            - ``{"type": "replacement", "text": CANNED_REFUSAL}`` — cuando
              D aborta o cuando B detecta la respuesta ensamblada flagged.
        """
        full_response = ""
        inner_stream = self.openai_client.chat_completion_stream(
            system_prompt=system_prompt,
            messages=historial,
            max_tokens=self.MAX_TOKENS_RESPUESTA,
        )

        for i, delta in enumerate(inner_stream):
            # ---- Hook D: first-chunk pre-check (defence in depth) --------
            # Si el PRIMER chunk del LLM es flagged por el provider de
            # moderación, abortamos el stream sin reenviar el chunk al
            # cliente, drenamos el resto silenciosamente, persistimos
            # CANNED_REFUSAL, y emitimos el marker de replacement.
            if i == 0:
                try:
                    self._moderar_salida(delta)
                except ContenidoBloqueadoError:
                    # Cierra el stream del SDK de OpenAI para liberar la
                    # conexión HTTP subyacente. La API puede ser un iterador
                    # de Python plano (tests) que no expone ``close``; en ese
                    # caso el GC cierra el generator al retornar.
                    close = getattr(inner_stream, "close", None)
                    if close is not None:
                        close()
                    MensajeCopilot.objects.create(
                        conversacion=conversacion,
                        rol=MensajeCopilot.Rol.ASSISTANT,
                        contenido=CANNED_REFUSAL,
                        tokens_usados=0,
                    )
                    conversacion.save(update_fields=["ultima_actividad"])
                    yield {"type": "replacement", "text": CANNED_REFUSAL}
                    return

            full_response += delta
            yield delta

        # ---- Hook B: post-stream replacement -----------------------------
        # Una vez ensamblada la respuesta completa, la moderamos. Si está
        # flagged: persistimos CANNED_REFUSAL y emitimos el marker para
        # que el cliente reemplace el texto streameado. Si está clean:
        # persistimos la respuesta completa tal cual (sin marker).
        if full_response:
            try:
                self._moderar_salida(full_response)
                contenido_a_persistir = full_response
                replacement_marker = None
            except ContenidoBloqueadoError:
                contenido_a_persistir = CANNED_REFUSAL
                replacement_marker = {"type": "replacement", "text": CANNED_REFUSAL}

            MensajeCopilot.objects.create(
                conversacion=conversacion,
                rol=MensajeCopilot.Rol.ASSISTANT,
                contenido=contenido_a_persistir,
                tokens_usados=0,
            )
            conversacion.save(update_fields=["ultima_actividad"])

            if replacement_marker is not None:
                yield replacement_marker

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
            "- Para calificaciones: muestra las notas y reportá el promedio ponderado por "
            "materia y el promedio general tal como aparecen en los datos. Podés responder "
            "directamente cuando el usuario pregunta '¿cuál es mi promedio?'. NO realices "
            "cálculos hipotéticos como '¿qué pasaría si cambiara la nota X a Y?'.\n"
            "- Para consultas de navegación: usa ÚNICA Y EXCLUSIVAMENTE los pasos de la "
            "guía de navegación provista en los datos del usuario. NUNCA inventes pasos, "
            "secciones ni rutas que no aparezcan en esa guía. Si el usuario pregunta por "
            "una acción específica, respondé SOLO con esa sección de la guía. No menciones "
            "secretarías presenciales, soporte técnico ni ningún canal externo a la "
            "plataforma — todas las instrucciones son dentro del sistema web.\n"
        )
