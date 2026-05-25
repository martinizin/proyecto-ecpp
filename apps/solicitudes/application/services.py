"""
Application services (use cases) for the Solicitudes bounded context.

Sprint 3 — HU18/HU19: Solicitudes de recalificación y justificación.
"""

from decimal import Decimal, InvalidOperation

from apps.shared.email_utils import enviar_email_html
from django.db import models, transaction
from django.utils import timezone

from apps.academico.infrastructure.models import Matricula
from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.infrastructure.models import (
    Calificacion,
    LogCalificacion,
)
from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.application.dtos import BulkResultadoDTO
from apps.solicitudes.application.notifications import (
    notificar_nueva_justificacion,
)
from apps.solicitudes.domain.exceptions import (
    ArchivoInvalidoError,
    CamposObligatoriosFaltantesError,
    FechaCertificadoInvalidaError,
    MaximoArchivosExcedidoError,
)
from apps.solicitudes.domain.services import CertificadoValidationService
from apps.solicitudes.infrastructure.models import (
    ArchivoSolicitud,
    CertificadoJustificacion,
    HistorialSolicitud,
    Solicitud,
)
from apps.usuarios.infrastructure.models import Usuario

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class SolicitudAppService:
    """Handles creation and listing of student requests."""

    # ── Validaciones comunes ──────────────────────────────────────────

    @staticmethod
    def _validar_archivo(archivo):
        """Validate uploaded file: size ≤ 5MB, allowed extensions."""
        if archivo is None:
            return None
        if archivo.size > MAX_FILE_SIZE:
            return "El archivo no puede superar los 5 MB."
        ext = archivo.name.rsplit(".", 1)[-1].lower() if "." in archivo.name else ""
        if ext not in ("pdf", "jpg", "jpeg", "png"):
            return "Solo se permiten archivos PDF, JPG o PNG."
        return None

    # ── Recalificación ────────────────────────────────────────────────

    @staticmethod
    def obtener_calificaciones_reclamables(estudiante):
        """Return calificaciones the student can request rectification for.

        Grades in COMPLETO or VALIDADO paralelos, in active periods, with active enrollment.
        Students can request rectification once the docente sends the planilla (COMPLETO).
        """
        return (
            Calificacion.objects.filter(
                estudiante=estudiante,
                evaluacion__paralelo__registro_calificaciones__estado__in=[
                    "completo",
                    "validado",
                ],
                evaluacion__paralelo__periodo__activo=True,
                evaluacion__paralelo__matriculas__estudiante=estudiante,
                evaluacion__paralelo__matriculas__estado=Matricula.Estado.ACTIVA,
            )
            .select_related(
                "evaluacion__paralelo__asignatura",
                "evaluacion__paralelo__periodo",
            )
            .distinct()
            .order_by(
                "evaluacion__paralelo__asignatura__codigo",
                "evaluacion__tipo",
            )
        )

    @staticmethod
    def crear_recalificacion(estudiante, calificacion_id, descripcion, archivo=None):
        """Create a grade rectification request.

        Returns:
            dict with 'ok' (bool) and 'error' (str) or 'solicitud' (Solicitud).
        """
        # Validate calificacion belongs to student
        try:
            calificacion = Calificacion.objects.select_related(
                "evaluacion__paralelo__asignatura",
                "evaluacion__paralelo__docente",
                "evaluacion__paralelo__periodo",
            ).get(pk=calificacion_id, estudiante=estudiante)
        except Calificacion.DoesNotExist:
            return {"ok": False, "error": "Calificación no encontrada."}

        paralelo = calificacion.evaluacion.paralelo

        # Must be in active period
        if not paralelo.periodo.activo:
            return {
                "ok": False,
                "error": "Solo puede solicitar recalificación en el período activo.",
            }

        # Must be COMPLETO or VALIDADO (planilla already sent)
        registro = getattr(paralelo, "registro_calificaciones", None)
        if not registro or registro.estado not in ("completo", "validado"):
            return {
                "ok": False,
                "error": "Solo puede reclamar evaluaciones cuya planilla ya fue enviada.",
            }

        # Validate file
        error_archivo = SolicitudAppService._validar_archivo(archivo)
        if error_archivo:
            return {"ok": False, "error": error_archivo}

        # Validate descripcion
        if not descripcion or not descripcion.strip():
            return {"ok": False, "error": "Debe indicar el motivo de la solicitud."}

        # Calculate numero_solicitud
        solicitudes_previas = Solicitud.objects.filter(
            estudiante=estudiante,
            calificacion=calificacion,
            tipo=Solicitud.TipoSolicitud.RECTIFICACION,
        ).count()
        numero = solicitudes_previas + 1
        requiere_secretaria = numero > 1

        solicitud = Solicitud.objects.create(
            tipo=Solicitud.TipoSolicitud.RECTIFICACION,
            estudiante=estudiante,
            calificacion=calificacion,
            descripcion=descripcion.strip(),
            archivo_adjunto=archivo,
            numero_solicitud=numero,
            requiere_secretaria=requiere_secretaria,
        )

        # Notify based on flow
        if requiere_secretaria:
            # 2da+: notify secretaría (they must validate first)
            SolicitudAppService._notificar_secretaria_recalificacion(solicitud, calificacion)
        else:
            # 1ra: notify docente directly
            SolicitudAppService._notificar_docente_recalificacion(solicitud, calificacion)

        return {"ok": True, "solicitud": solicitud}

    # ── Justificación de inasistencia ─────────────────────────────────

    @staticmethod
    def obtener_inasistencias_justificables(estudiante):
        """Return AUSENTE attendance records the student can justify.

        Only in active periods with active enrollment.
        """
        return (
            Asistencia.objects.filter(
                estudiante=estudiante,
                estado=Asistencia.Estado.AUSENTE,
                paralelo__periodo__activo=True,
                paralelo__matriculas__estudiante=estudiante,
                paralelo__matriculas__estado=Matricula.Estado.ACTIVA,
            )
            .select_related("paralelo__asignatura", "paralelo__periodo")
            .distinct()
            .order_by("-fecha")
        )

    @staticmethod
    def crear_justificacion(estudiante, asistencia_id, descripcion, archivo=None):
        """Create an absence justification request.

        Returns:
            dict with 'ok' (bool) and 'error' (str) or 'solicitud' (Solicitud).
        """
        # Validate asistencia belongs to student and is AUSENTE
        try:
            asistencia = Asistencia.objects.select_related(
                "paralelo__asignatura", "paralelo__periodo"
            ).get(
                pk=asistencia_id,
                estudiante=estudiante,
                estado=Asistencia.Estado.AUSENTE,
            )
        except Asistencia.DoesNotExist:
            return {
                "ok": False,
                "error": "Registro de inasistencia no encontrado o ya fue justificado.",
            }

        # Must be in active period
        if not asistencia.paralelo.periodo.activo:
            return {
                "ok": False,
                "error": "Solo puede justificar inasistencias del período activo.",
            }

        # Validate file
        error_archivo = SolicitudAppService._validar_archivo(archivo)
        if error_archivo:
            return {"ok": False, "error": error_archivo}

        # Validate descripcion
        if not descripcion or not descripcion.strip():
            return {"ok": False, "error": "Debe indicar el motivo de la justificación."}

        # Check for duplicate pending request
        solicitud_existente = Solicitud.objects.filter(
            estudiante=estudiante,
            asistencia=asistencia,
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
            estado__in=[
                Solicitud.EstadoSolicitud.PENDIENTE,
                Solicitud.EstadoSolicitud.EN_REVISION,
            ],
        ).exists()
        if solicitud_existente:
            return {
                "ok": False,
                "error": "Ya tiene una solicitud pendiente para esta inasistencia.",
            }

        numero = (
            Solicitud.objects.filter(
                estudiante=estudiante,
                asistencia=asistencia,
                tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
            ).count()
            + 1
        )

        solicitud = Solicitud.objects.create(
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
            estudiante=estudiante,
            asistencia=asistencia,
            descripcion=descripcion.strip(),
            archivo_adjunto=archivo,
            numero_solicitud=numero,
        )

        notificar_nueva_justificacion(solicitud)
        return {"ok": True, "solicitud": solicitud}

    # ── Listar mis solicitudes ────────────────────────────────────────

    @staticmethod
    def obtener_mis_solicitudes(estudiante, tipo=None):
        """Return all solicitudes for a student, optionally filtered by tipo."""
        qs = Solicitud.objects.filter(estudiante=estudiante).select_related(
            "calificacion__evaluacion__paralelo__asignatura",
            "asistencia__paralelo__asignatura",
        )
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    # ── Notificaciones ────────────────────────────────────────────────

    @staticmethod
    def _notificar_docente_recalificacion(solicitud, calificacion):
        """Send in-app notification + email to the docente."""
        docente = calificacion.evaluacion.paralelo.docente
        if not docente:
            return

        asignatura = calificacion.evaluacion.paralelo.asignatura.nombre
        evaluacion = calificacion.evaluacion.get_tipo_display()
        estudiante_nombre = solicitud.estudiante.get_full_name()

        titulo = f"Solicitud de recalificación — {asignatura}"
        mensaje = (
            f"El estudiante {estudiante_nombre} ha solicitado "
            f"recalificación de {evaluacion} en {asignatura}.\n\n"
            f"Motivo: {solicitud.descripcion}"
        )

        # In-app notification
        Notificacion.objects.create(
            destinatario=docente,
            tipo=Notificacion.Tipo.SOLICITUD_RECALIFICACION,
            titulo=titulo,
            mensaje=mensaje,
            url="/solicitudes/pendientes/",
        )

        # Email notification
        if docente.email:
            try:
                enviar_email_html(
                    destinatario=docente.email,
                    asunto=f"[ECPP] {titulo}",
                    template="emails/notificacion_general.html",
                    contexto={"titulo": titulo, "mensaje": mensaje},
                )
            except Exception:
                pass  # Don't break the flow if email fails

    @staticmethod
    def _notificar_secretaria_recalificacion(solicitud, calificacion):
        """Notify all secretaría users about a 2da+ recalificación request."""
        asignatura = calificacion.evaluacion.paralelo.asignatura.nombre
        evaluacion = calificacion.evaluacion.get_tipo_display()
        estudiante_nombre = solicitud.estudiante.get_full_name()

        titulo = f"Recalificación requiere validación — {asignatura}"
        mensaje = (
            f"El estudiante {estudiante_nombre} ha presentado la solicitud "
            f"#{solicitud.numero_solicitud} de recalificación para "
            f"{evaluacion} en {asignatura}.\n\n"
            f"Requiere validación de secretaría antes de escalar al docente."
        )

        secretarias = Usuario.objects.filter(rol="secretaria", is_active=True)
        for sec in secretarias:
            Notificacion.objects.create(
                destinatario=sec,
                tipo=Notificacion.Tipo.SOLICITUD_RECALIFICACION,
                titulo=titulo,
                mensaje=mensaje,
                url="/solicitudes/secretaria/",
            )
            if sec.email:
                try:
                    enviar_email_html(
                        destinatario=sec.email,
                        asunto=f"[ECPP] {titulo}",
                        template="emails/notificacion_general.html",
                        contexto={"titulo": titulo, "mensaje": mensaje},
                    )
                except Exception:
                    pass

    @staticmethod
    def _notificar_inspectores_justificacion(solicitud, asistencia):
        """Deprecated shim — kept for backwards compatibility.

        The real logic now lives in
        :func:`apps.solicitudes.application.notifications.notificar_nueva_justificacion`.
        This wrapper exists so external code (if any) that still imports the
        old name keeps working. The Slice 2 refactor removed all internal
        callers; new code MUST call the helper directly.
        """
        notificar_nueva_justificacion(solicitud)

    # ── HU19: Listados para docente / secretaría / inspector ──────────

    @staticmethod
    def obtener_pendientes_docente(docente):
        """Solicitudes de recalificación pendientes en paralelos del docente.

        Includes PENDIENTE (1ra) and EN_REVISION (escaladas por secretaría).
        """
        return (
            Solicitud.objects.filter(
                tipo=Solicitud.TipoSolicitud.RECTIFICACION,
                calificacion__evaluacion__paralelo__docente=docente,
            )
            .filter(
                models.Q(
                    estado=Solicitud.EstadoSolicitud.PENDIENTE,
                    requiere_secretaria=False,
                )
                | models.Q(
                    estado=Solicitud.EstadoSolicitud.EN_REVISION,
                )
            )
            .select_related(
                "estudiante",
                "calificacion__evaluacion__paralelo__asignatura",
            )
            .order_by("-fecha_creacion")
        )

    @staticmethod
    def obtener_pendientes_secretaria():
        """Solicitudes que requieren validación de secretaría.

        Recalificación 2da+: PENDIENTE con requiere_secretaria=True.
        """
        return (
            Solicitud.objects.filter(
                tipo=Solicitud.TipoSolicitud.RECTIFICACION,
                estado=Solicitud.EstadoSolicitud.PENDIENTE,
                requiere_secretaria=True,
            )
            .select_related(
                "estudiante",
                "calificacion__evaluacion__paralelo__asignatura",
                "calificacion__evaluacion__paralelo__docente",
            )
            .order_by("-fecha_creacion")
        )

    @staticmethod
    def obtener_pendientes_justificacion():
        """Solicitudes de justificación pendientes (para inspector o secretaría)."""
        return (
            Solicitud.objects.filter(
                tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
                estado__in=[
                    Solicitud.EstadoSolicitud.PENDIENTE,
                    Solicitud.EstadoSolicitud.EN_REVISION,
                ],
            )
            .select_related(
                "estudiante",
                "asistencia__paralelo__asignatura",
            )
            .order_by("-fecha_creacion")
        )

    # ── HU19: Transiciones de estado ──────────────────────────────────

    @staticmethod
    def _registrar_historial(solicitud, estado_anterior, estado_nuevo, usuario, comentario=""):
        """Create a HistorialSolicitud entry."""
        HistorialSolicitud.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            cambiado_por=usuario,
            comentario=comentario,
        )

    @staticmethod
    def _notificar_estudiante_cambio(solicitud, estado_nuevo, comentario=""):
        """Notify student (in-app + email) about state change."""
        estados_display = dict(Solicitud.EstadoSolicitud.choices)
        tipo_display = solicitud.get_tipo_display()
        estado_label = estados_display.get(estado_nuevo, estado_nuevo)

        titulo = f"Su {tipo_display} fue actualizada a: {estado_label}"
        mensaje = f"Su solicitud #{solicitud.numero_solicitud} cambió a {estado_label}."
        if comentario:
            mensaje += f"\n\nComentario: {comentario}"

        Notificacion.objects.create(
            destinatario=solicitud.estudiante,
            tipo=Notificacion.Tipo.CAMBIO_ESTADO_SOLICITUD,
            titulo=titulo,
            mensaje=mensaje,
            url="/solicitudes/mis-solicitudes/",
        )

        if solicitud.estudiante.email:
            try:
                enviar_email_html(
                    destinatario=solicitud.estudiante.email,
                    asunto=f"[ECPP] {titulo}",
                    template="emails/notificacion_general.html",
                    contexto={"titulo": titulo, "mensaje": mensaje},
                )
            except Exception:
                pass

    @staticmethod
    def tomar_solicitud(solicitud_id, usuario):
        """Move solicitud from PENDIENTE to EN_REVISION.

        Used by docente (1ra recalificación) or inspector/secretaría (justificación).
        Returns dict with 'ok' and 'error' or 'solicitud'.
        """
        try:
            solicitud = Solicitud.objects.select_related("estudiante").get(pk=solicitud_id)
        except Solicitud.DoesNotExist:
            return {"ok": False, "error": "Solicitud no encontrada."}

        if solicitud.estado != Solicitud.EstadoSolicitud.PENDIENTE:
            return {"ok": False, "error": "Solo se pueden tomar solicitudes pendientes."}

        estado_anterior = solicitud.estado
        solicitud.estado = Solicitud.EstadoSolicitud.EN_REVISION
        solicitud.save(update_fields=["estado"])

        SolicitudAppService._registrar_historial(
            solicitud, estado_anterior, solicitud.estado, usuario, "Solicitud tomada."
        )
        SolicitudAppService._notificar_estudiante_cambio(solicitud, solicitud.estado)
        return {"ok": True, "solicitud": solicitud}

    @staticmethod
    def escalar_a_docente(solicitud_id, usuario, comentario=""):
        """Secretaría validates 2da+ recalificación and escalates to docente.

        PENDIENTE → EN_REVISION. Notifies docente.
        """
        try:
            solicitud = Solicitud.objects.select_related(
                "estudiante",
                "calificacion__evaluacion__paralelo__docente",
                "calificacion__evaluacion__paralelo__asignatura",
            ).get(pk=solicitud_id)
        except Solicitud.DoesNotExist:
            return {"ok": False, "error": "Solicitud no encontrada."}

        if solicitud.estado != Solicitud.EstadoSolicitud.PENDIENTE:
            return {"ok": False, "error": "Solo se pueden escalar solicitudes pendientes."}

        if not solicitud.requiere_secretaria:
            return {
                "ok": False,
                "error": "Esta solicitud no requiere validación de secretaría.",
            }

        estado_anterior = solicitud.estado
        solicitud.estado = Solicitud.EstadoSolicitud.EN_REVISION
        solicitud.save(update_fields=["estado"])

        SolicitudAppService._registrar_historial(
            solicitud,
            estado_anterior,
            solicitud.estado,
            usuario,
            comentario or "Validada por secretaría, escalada a docente.",
        )

        # Notify docente
        docente = solicitud.calificacion.evaluacion.paralelo.docente
        if docente:
            asignatura = solicitud.calificacion.evaluacion.paralelo.asignatura.nombre
            Notificacion.objects.create(
                destinatario=docente,
                tipo=Notificacion.Tipo.SOLICITUD_RECALIFICACION,
                titulo=f"Solicitud de recalificación escalada — {asignatura}",
                mensaje=(
                    f"Secretaría validó la solicitud #{solicitud.numero_solicitud} "
                    f"de {solicitud.estudiante.get_full_name()}. "
                    f"Requiere su resolución."
                ),
                url="/solicitudes/pendientes/",
            )

        SolicitudAppService._notificar_estudiante_cambio(
            solicitud, solicitud.estado, "Su solicitud fue validada por secretaría."
        )
        return {"ok": True, "solicitud": solicitud}

    @staticmethod
    def resolver_solicitud(solicitud_id, usuario, accion, comentario="", nueva_nota=None):
        """Approve or reject a solicitud.

        Args:
            solicitud_id: PK of the solicitud.
            usuario: User resolving (docente/inspector/secretaría).
            accion: 'aprobar' or 'rechazar'.
            comentario: Resolution comment (required for rejection).
            nueva_nota: New grade (required when approving recalificación).

        Returns:
            dict with 'ok' and 'error' or 'solicitud'.
        """
        if accion not in ("aprobar", "rechazar"):
            return {"ok": False, "error": "Acción no válida."}

        try:
            solicitud = Solicitud.objects.select_related(
                "estudiante",
                "calificacion__evaluacion__paralelo__asignatura",
                "calificacion__evaluacion__paralelo__docente",
                "asistencia__paralelo__asignatura",
            ).get(pk=solicitud_id)
        except Solicitud.DoesNotExist:
            return {"ok": False, "error": "Solicitud no encontrada."}

        # Must be PENDIENTE (1ra sin secretaría) or EN_REVISION
        estados_validos = [
            Solicitud.EstadoSolicitud.PENDIENTE,
            Solicitud.EstadoSolicitud.EN_REVISION,
        ]
        if solicitud.estado not in estados_validos:
            return {"ok": False, "error": "Esta solicitud ya fue resuelta."}

        if accion == "rechazar" and not comentario.strip():
            return {"ok": False, "error": "Debe indicar el motivo del rechazo."}

        # Approve recalificación: validate nueva_nota
        if accion == "aprobar" and solicitud.tipo == Solicitud.TipoSolicitud.RECTIFICACION:
            if nueva_nota is None or str(nueva_nota).strip() == "":
                return {"ok": False, "error": "Debe indicar la nueva nota."}
            try:
                nueva_nota_decimal = Decimal(str(nueva_nota))
            except (InvalidOperation, ValueError):
                return {"ok": False, "error": "La nota debe ser un valor numérico."}
            if nueva_nota_decimal < 0 or nueva_nota_decimal > 20:
                return {"ok": False, "error": "La nota debe estar entre 0 y 20."}
            if solicitud.calificacion and nueva_nota_decimal < solicitud.calificacion.nota:
                return {
                    "ok": False,
                    "error": "La nueva nota no puede ser menor a la nota actual.",
                }

        estado_anterior = solicitud.estado
        if accion == "aprobar":
            solicitud.estado = Solicitud.EstadoSolicitud.APROBADA
        else:
            solicitud.estado = Solicitud.EstadoSolicitud.RECHAZADA

        solicitud.respuesta = comentario.strip()
        solicitud.resuelto_por = usuario
        solicitud.fecha_resolucion = timezone.now()
        solicitud.save(update_fields=["estado", "respuesta", "resuelto_por", "fecha_resolucion"])

        SolicitudAppService._registrar_historial(
            solicitud, estado_anterior, solicitud.estado, usuario, comentario
        )

        # Side effects on approval
        if accion == "aprobar":
            if solicitud.tipo == Solicitud.TipoSolicitud.RECTIFICACION:
                SolicitudAppService._aplicar_recalificacion(solicitud, nueva_nota_decimal, usuario)
            elif solicitud.tipo == Solicitud.TipoSolicitud.JUSTIFICACION:
                SolicitudAppService._aplicar_justificacion(solicitud, usuario)

        SolicitudAppService._notificar_estudiante_cambio(solicitud, solicitud.estado, comentario)
        return {"ok": True, "solicitud": solicitud}

    @staticmethod
    def _aplicar_recalificacion(solicitud, nueva_nota, usuario):
        """Update the calificacion and create audit log."""
        calificacion = solicitud.calificacion
        if not calificacion:
            return

        valor_anterior = calificacion.nota
        calificacion.nota = nueva_nota
        calificacion.save(update_fields=["nota"])

        LogCalificacion.objects.create(
            calificacion=calificacion,
            evaluacion_info=str(calificacion.evaluacion),
            estudiante_info=(
                f"{solicitud.estudiante.get_full_name()} " f"({solicitud.estudiante.cedula})"
            ),
            accion=LogCalificacion.TipoAccion.RECALIFICACION,
            valor_anterior=valor_anterior,
            valor_nuevo=nueva_nota,
            realizado_por=usuario,
            motivo=(
                f"Recalificación aprobada — Solicitud #{solicitud.numero_solicitud}. "
                f"{solicitud.respuesta}"
            ),
        )

    @staticmethod
    def _aplicar_justificacion(solicitud, usuario):
        """Change asistencia from AUSENTE to JUSTIFICADO."""
        asistencia = solicitud.asistencia
        if not asistencia:
            return
        asistencia.estado = Asistencia.Estado.JUSTIFICADO
        asistencia.save(update_fields=["estado"])

        # Log macro: justificación de asistencia
        LogCalificacion.objects.create(
            accion=LogCalificacion.TipoAccion.JUSTIFICACION,
            estudiante_info=(
                f"{solicitud.estudiante.get_full_name()} ({solicitud.estudiante.cedula})"
            ),
            realizado_por=usuario,
            motivo=(
                f"Justificación aprobada — Solicitud #{solicitud.numero_solicitud}. "
                f"{solicitud.respuesta}"
            ),
        )


# --------------------------------------------------------------------------- #
# HU20 — Justificación con certificado categorizado
# --------------------------------------------------------------------------- #


class JustificacionCertificadoAppService:
    """Orchestrates HU20 absence-justification with categorized certificate.

    Sibling of :class:`SolicitudAppService.crear_justificacion` — the legacy
    flow remains intact for callers that only need the single-file flow.
    This service adds:

    * Per-tipo required-field validation via
      :class:`CertificadoValidationService`.
    * Multi-file uploads (up to ``MAX_ARCHIVOS``) with per-file extension
      and size validation.
    * Atomic ``transaction.atomic()`` wrapper so a mid-flight error
      rolls back the Solicitud + Certificado + Archivos together.
    * Reuses :func:`notificar_nueva_justificacion` (same notification
      semantics as HU18).

    Domain exceptions raised by this service are propagated unchanged so
    the presentation layer can map them to user-facing messages.
    """

    def crear_justificacion_con_certificado(
        self,
        asistencia,
        estudiante,
        tipo_certificado: str,
        datos_certificado: dict,
        archivos: list,
        motivo: str,
    ) -> Solicitud:
        """Create Solicitud + CertificadoJustificacion + ArchivoSolicitud rows.

        Validation order (fail-fast, before any DB write):

        1. ``len(archivos) <= MAX_ARCHIVOS``
        2. Each file passes ext + size validation
        3. ``datos_certificado`` contains all required fields for ``tipo_certificado``
        4. ``fecha_certificado <= today``

        After validation, everything is created inside a single
        ``transaction.atomic()`` block; the inspector notification is
        invoked once the block commits.
        """

        # 1) max files
        if len(archivos) > CertificadoValidationService.MAX_ARCHIVOS:
            raise MaximoArchivosExcedidoError(len(archivos))

        # 2) per-file validation (strict atomic — reject the whole batch on first bad file)
        for archivo in archivos:
            errores = CertificadoValidationService.validar_archivo(archivo.name, archivo.size)
            if errores:
                raise ArchivoInvalidoError(archivo.name, errores)

        # 3) required fields per tipo
        faltantes = CertificadoValidationService.validar_campos_obligatorios(
            tipo_certificado, datos_certificado
        )
        if faltantes:
            raise CamposObligatoriosFaltantesError(faltantes)

        # 4) fecha not in future
        fecha_cert = datos_certificado.get("fecha_certificado")
        if not CertificadoValidationService.validar_fecha_certificado(
            fecha_cert, timezone.localdate()
        ):
            raise FechaCertificadoInvalidaError()

        with transaction.atomic():
            numero = (
                Solicitud.objects.filter(
                    estudiante=estudiante,
                    asistencia=asistencia,
                    tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
                ).count()
                + 1
            )

            solicitud = Solicitud.objects.create(
                tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
                estudiante=estudiante,
                asistencia=asistencia,
                descripcion=(motivo or "").strip(),
                numero_solicitud=numero,
            )

            CertificadoJustificacion.objects.create(
                solicitud=solicitud,
                tipo=tipo_certificado,
                **{k: v for k, v in datos_certificado.items() if v is not None},
            )

            for archivo in archivos:
                ArchivoSolicitud.objects.create(
                    solicitud=solicitud,
                    archivo=archivo,
                    nombre_original=archivo.name,
                    tipo_mime=getattr(archivo, "content_type", "") or "",
                    tamanio_bytes=archivo.size,
                )

            notificar_nueva_justificacion(solicitud)

        return solicitud


# --------------------------------------------------------------------------- #
# HU21 - Resolucion de justificaciones por Inspector
# --------------------------------------------------------------------------- #


class InspectorResolucionAppService:
    """Thin wrapper over :meth:`SolicitudAppService.resolver_solicitud` for
    inspector-driven justification resolution (HU21).

    Adds three behaviors on top of the existing single-resolve flow:

    * **Idempotent skip**: a solicitud that is already APROBADA / RECHAZADA
      is returned unchanged: no new HistorialSolicitud, no double
      notification.
    * **Comentario validation for rechazar** (singular and bulk). Empty or
      whitespace-only comentario raises :class:`ValueError`. In the bulk
      path the check is **all-or-nothing**: it runs BEFORE the loop, so
      zero rows are touched if the comentario is invalid.
    * **Bulk semantics**: :meth:`procesar_bulk_resolucion` iterates the
      provided ids, applies the action per row inside its own
      ``transaction.atomic()`` block, and reports outcome via
      :class:`BulkResultadoDTO`. A failing row never aborts the batch.
    """

    def aprobar_justificacion(self, solicitud, inspector, comentario: str = ""):
        """Approve a single justification.

        Returns the (refreshed) :class:`Solicitud`. Idempotent on already
        resolved rows: the row is returned unchanged.
        """
        if solicitud.estado in (
            Solicitud.EstadoSolicitud.APROBADA,
            Solicitud.EstadoSolicitud.RECHAZADA,
        ):
            return solicitud

        resultado = SolicitudAppService.resolver_solicitud(
            solicitud_id=solicitud.pk,
            usuario=inspector,
            accion="aprobar",
            comentario=comentario or "",
        )
        if not resultado.get("ok"):
            raise RuntimeError(resultado.get("error", "Error al aprobar"))
        return resultado["solicitud"]

    def rechazar_justificacion(self, solicitud, inspector, comentario: str):
        """Reject a single justification.

        Requires a non-empty ``comentario`` (after stripping whitespace).
        Idempotent on already resolved rows.
        """
        if not comentario or not comentario.strip():
            raise ValueError("El comentario es obligatorio al rechazar.")

        if solicitud.estado in (
            Solicitud.EstadoSolicitud.APROBADA,
            Solicitud.EstadoSolicitud.RECHAZADA,
        ):
            return solicitud

        resultado = SolicitudAppService.resolver_solicitud(
            solicitud_id=solicitud.pk,
            usuario=inspector,
            accion="rechazar",
            comentario=comentario,
        )
        if not resultado.get("ok"):
            raise RuntimeError(resultado.get("error", "Error al rechazar"))
        return resultado["solicitud"]

    def procesar_bulk_resolucion(
        self,
        ids: list[int],
        inspector,
        accion: str,
        comentario: str = "",
    ) -> BulkResultadoDTO:
        """Apply ``accion`` to every solicitud whose pk is in ``ids``.

        All-or-nothing comentario validation for ``rechazar`` runs BEFORE
        the loop. If it fails, ``ValueError`` is raised and zero rows
        are touched.

        Per-row :func:`~django.db.transaction.atomic` so a single row
        failure does not abort the batch. Rows already in a terminal
        state are silently skipped and counted in ``omitidas``.
        """
        if accion == "rechazar" and (not comentario or not comentario.strip()):
            raise ValueError("El comentario es obligatorio al rechazar en bulk.")

        resultado = BulkResultadoDTO()
        if not ids:
            return resultado

        solicitudes = Solicitud.objects.filter(
            pk__in=ids,
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        )

        for solicitud in solicitudes:
            if solicitud.estado in (
                Solicitud.EstadoSolicitud.APROBADA,
                Solicitud.EstadoSolicitud.RECHAZADA,
            ):
                resultado.omitidas_ids.append(solicitud.pk)
                continue
            try:
                with transaction.atomic():
                    if accion == "aprobar":
                        self.aprobar_justificacion(solicitud, inspector, comentario)
                    elif accion == "rechazar":
                        self.rechazar_justificacion(solicitud, inspector, comentario)
                    else:
                        # Invalid action: count as omitida.
                        raise ValueError(f"Accion invalida: {accion}")
                resultado.procesadas += 1
            except Exception:
                # Per-row atomicity: failure here only impacts THIS row.
                resultado.omitidas_ids.append(solicitud.pk)

        resultado.omitidas = len(resultado.omitidas_ids)
        return resultado
