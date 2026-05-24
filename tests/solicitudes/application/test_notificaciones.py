"""Tests for the notification helper extracted from SolicitudAppService."""

import pytest

from apps.notificaciones.infrastructure.models import Notificacion
from apps.solicitudes.application.notifications import (
    notificar_nueva_justificacion,
)
from apps.solicitudes.infrastructure.models import Solicitud
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    SolicitudFactory,
)


def _build_solicitud_justificacion(neutral_actor):
    """Build a persisted Solicitud of tipo JUSTIFICACION linked to an asistencia.

    ``neutral_actor`` must be a non-inspector Usuario; it is used as
    ``matriculado_por`` so MatriculaFactory does not implicitly create
    an extra inspector that would skew notification counts.
    """
    periodo = PeriodoFactory(activo=True)
    paralelo = ParaleloFactory(periodo=periodo)
    estudiante = EstudianteFactory()
    estudiante.save()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo, matriculado_por=neutral_actor)
    asistencia = AsistenciaFactory(estudiante=estudiante, paralelo=paralelo)
    solicitud = SolicitudFactory(
        tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        estudiante=estudiante,
        asistencia=asistencia,
        descripcion="Estuve enfermo",
    )
    return solicitud


@pytest.mark.django_db
class TestNotificarNuevaJustificacion:
    def setup_method(self):
        # Neutral non-inspector actor used for MatriculaFactory.matriculado_por
        # so we control the inspector count exactly.
        self.actor = DocenteFactory()
        self.actor.save()

    def test_notifica_a_inspector_activo(self):
        inspector = InspectorFactory()
        inspector.save()
        solicitud = _build_solicitud_justificacion(self.actor)

        notificar_nueva_justificacion(solicitud)

        notif = Notificacion.objects.filter(
            destinatario=inspector,
            tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION,
        )
        assert notif.count() == 1
        notificacion = notif.first()
        assert "justificación" in notificacion.titulo.lower()
        assert solicitud.estudiante.get_full_name() in notificacion.mensaje
        assert solicitud.descripcion in notificacion.mensaje

    def test_no_falla_si_no_hay_inspectores(self):
        solicitud = _build_solicitud_justificacion(self.actor)

        # No inspector exists — should be a silent no-op
        notificar_nueva_justificacion(solicitud)

        assert (
            Notificacion.objects.filter(tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION).count()
            == 0
        )

    def test_notifica_a_multiples_inspectores(self):
        InspectorFactory().save()
        InspectorFactory().save()
        solicitud = _build_solicitud_justificacion(self.actor)

        notificar_nueva_justificacion(solicitud)

        assert (
            Notificacion.objects.filter(tipo=Notificacion.Tipo.SOLICITUD_JUSTIFICACION).count()
            == 2
        )

    def test_ignora_inspector_inactivo(self):
        inspector = InspectorFactory(is_active=False)
        inspector.save()
        solicitud = _build_solicitud_justificacion(self.actor)

        notificar_nueva_justificacion(solicitud)

        assert Notificacion.objects.filter(destinatario=inspector).count() == 0
