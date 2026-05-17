"""
Application services (use cases) for the Solicitudes bounded context.

Sprint 3 — HU18: Solicitudes de recalificación y justificación de inasistencia.
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.academico.infrastructure.models import Matricula
from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.infrastructure.models import Calificacion
from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.infrastructure.models import Solicitud

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

        Only grades in VALIDADO paralelos, in active periods, with active enrollment.
        """
        return (
            Calificacion.objects.filter(
                estudiante=estudiante,
                evaluacion__paralelo__registro_calificaciones__estado="validado",
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

        # Must be VALIDADO
        registro = getattr(paralelo, "registro_calificaciones", None)
        if not registro or registro.estado != "validado":
            return {
                "ok": False,
                "error": "Solo puede reclamar evaluaciones con notas validadas.",
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

        # Notify docente (in-app + email)
        SolicitudAppService._notificar_docente_recalificacion(
            solicitud, calificacion
        )

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
                send_mail(
                    subject=f"[ECPPP] {titulo}",
                    message=mensaje,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[docente.email],
                    fail_silently=True,
                )
            except Exception:
                pass  # Don't break the flow if email fails
