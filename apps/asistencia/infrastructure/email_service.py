"""
Email service for attendance alerts.
Infrastructure layer — notifies inspectors when students exceed 5% absence.
"""

import logging

from apps.notificaciones.infrastructure.models import Notificacion
from apps.shared.email_utils import enviar_email_html
from apps.usuarios.infrastructure.models import Usuario

logger = logging.getLogger(__name__)


def send_alerta_inasistencia(
    inspector_email: str,
    estudiante_nombre: str,
    porcentaje: float,
    asignatura_nombre: str,
    paralelo_nombre: str,
) -> None:
    """
    Send an absence alert email to a single inspector.
    """
    enviar_email_html(
        destinatario=inspector_email,
        asunto="ECPP — Alerta de inasistencia",
        template="emails/alerta_inasistencia.html",
        contexto={
            "estudiante_nombre": estudiante_nombre,
            "asignatura_nombre": asignatura_nombre,
            "paralelo_nombre": paralelo_nombre,
            "porcentaje": porcentaje,
        },
        fail_silently=True,
    )


def notificar_alertas_inasistencia(alertas: list, paralelo) -> None:
    """
    Send absence alert emails to all active inspectors for each alerta.

    Args:
        alertas: List of dicts with estudiante_id, porcentaje_inasistencia, paralelo.
        paralelo: Paralelo model instance.
    """
    try:
        inspectores = Usuario.objects.filter(rol="inspector", is_active=True)
        if not inspectores.exists():
            logger.warning("No hay inspectores activos para notificar alertas.")
            return

        for alerta in alertas:
            estudiante = Usuario.objects.get(pk=alerta["estudiante_id"])
            estudiante_nombre = estudiante.get_full_name() or estudiante.username
            porcentaje = alerta["porcentaje_inasistencia"]
            asignatura_nombre = paralelo.asignatura.nombre
            paralelo_nombre = paralelo.nombre

            for inspector in inspectores:
                send_alerta_inasistencia(
                    inspector_email=inspector.email,
                    estudiante_nombre=estudiante_nombre,
                    porcentaje=porcentaje,
                    asignatura_nombre=asignatura_nombre,
                    paralelo_nombre=paralelo_nombre,
                )

        logger.info("Alertas de inasistencia enviadas a %d inspector(es).", inspectores.count())

        # Create in-app notifications for each inspector
        try:
            notificaciones = []
            for alerta in alertas:
                estudiante = Usuario.objects.get(pk=alerta["estudiante_id"])
                estudiante_nombre = estudiante.get_full_name() or estudiante.username
                porcentaje = alerta["porcentaje_inasistencia"]
                asignatura_nombre = paralelo.asignatura.nombre
                paralelo_nombre = paralelo.nombre

                for inspector in inspectores:
                    notificaciones.append(
                        Notificacion(
                            destinatario=inspector,
                            tipo=Notificacion.Tipo.ALERTA_INASISTENCIA,
                            titulo="Alerta de inasistencia",
                            mensaje=(
                                f"{estudiante_nombre} tiene {porcentaje}% de inasistencia "
                                f"en {asignatura_nombre} (Paralelo {paralelo_nombre})"
                            ),
                            url="/asistencia/supervision/",
                        )
                    )
            if notificaciones:
                Notificacion.objects.bulk_create(notificaciones)
                logger.info(
                    "Creadas %d notificaciones in-app para inspectores.",
                    len(notificaciones),
                )
        except Exception:
            logger.exception("Error al crear notificaciones in-app.")

    except Exception:
        logger.exception("Error al enviar alertas de inasistencia por email.")
