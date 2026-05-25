"""Notification helpers for the Solicitudes bounded context.

Extracted from ``SolicitudAppService._notificar_inspectores_justificacion``
so both the legacy HU18 flow and the new HU20 certificate flow can share
the exact same in-app + email side effects without duplicating logic.
"""

from __future__ import annotations

from apps.notificaciones.infrastructure.models import Notificacion
from apps.shared.email_utils import enviar_email_html
from apps.solicitudes.infrastructure.models import Solicitud
from apps.usuarios.infrastructure.models import Usuario


def notificar_nueva_justificacion(solicitud: Solicitud) -> None:
    """Notify every active inspector about a new absence-justification request.

    Side effects (identical to the legacy private method this replaces):

    * Creates one :class:`Notificacion` per active inspector with
      ``tipo = SOLICITUD_JUSTIFICACION``.
    * Sends an HTML email per inspector that has an ``email`` set.
      Email errors are swallowed so the solicitud creation flow never
      breaks because the SMTP server is unavailable.

    The function is a no-op when no inspectors exist or when the solicitud
    has no related asistencia (defensive: the HU20 atomic flow always
    builds one, but the helper must not crash on partial data).
    """

    asistencia = solicitud.asistencia
    if asistencia is None:
        return

    asignatura = asistencia.paralelo.asignatura.nombre
    estudiante_nombre = solicitud.estudiante.get_full_name()

    titulo = f"Solicitud de justificación — {asignatura}"
    mensaje = (
        f"El estudiante {estudiante_nombre} ha solicitado "
        f"justificación de inasistencia en {asignatura}.\n\n"
        f"Motivo: {solicitud.descripcion}"
    )

    inspectores = Usuario.objects.filter(rol="inspector", is_active=True)
    for inspector in inspectores:
        Notificacion.objects.create(
            destinatario=inspector,
            tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION,
            titulo=titulo,
            mensaje=mensaje,
            url="/solicitudes/justificaciones/",
        )
        if inspector.email:
            try:
                enviar_email_html(
                    destinatario=inspector.email,
                    asunto=f"[ECPP] {titulo}",
                    template="emails/notificacion_general.html",
                    contexto={"titulo": titulo, "mensaje": mensaje},
                )
            except Exception:
                # Email is best-effort: never break the solicitud flow.
                pass
