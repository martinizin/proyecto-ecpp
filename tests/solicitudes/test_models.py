"""Tests for Solicitud model."""

import pytest

from apps.solicitudes.infrastructure.models import Solicitud
from tests.factories import SolicitudFactory


pytestmark = pytest.mark.django_db


class TestSolicitud:
    """Tests for Solicitud model."""

    def test_create_solicitud(self):
        solicitud = SolicitudFactory()
        assert solicitud.pk is not None
        assert solicitud.descripcion == "Solicitud de prueba"
        assert solicitud.fecha_creacion is not None

    def test_default_estado_pendiente(self):
        """Default estado should be 'pendiente'."""
        solicitud = SolicitudFactory()
        assert solicitud.estado == Solicitud.EstadoSolicitud.PENDIENTE
        assert solicitud.estado == "pendiente"

    def test_tipo_choices(self):
        """Two solicitud types should be defined."""
        choices = [c[0] for c in Solicitud.TipoSolicitud.choices]
        assert "rectificacion" in choices
        assert "justificacion" in choices
        assert len(choices) == 2

    def test_estado_choices(self):
        """Three solicitud states should be defined."""
        choices = [c[0] for c in Solicitud.EstadoSolicitud.choices]
        assert "pendiente" in choices
        assert "aprobada" in choices
        assert "rechazada" in choices
        assert len(choices) == 3

    def test_str(self):
        solicitud = SolicitudFactory()
        expected = (
            f"{solicitud.get_tipo_display()} - {solicitud.estudiante} "
            f"({solicitud.get_estado_display()})"
        )
        assert str(solicitud) == expected

    def test_estudiante_is_student_role(self):
        """Solicitud should reference a student user."""
        solicitud = SolicitudFactory()
        assert solicitud.estudiante.rol == "estudiante"

    def test_ordering_by_fecha_creacion_desc(self):
        """Solicitudes should be ordered by fecha_creacion descending."""
        s1 = SolicitudFactory()
        s2 = SolicitudFactory()
        solicitudes = list(Solicitud.objects.all())
        # s2 was created after s1, so it should come first (desc)
        assert solicitudes[0] == s2
        assert solicitudes[1] == s1

    def test_create_justificacion(self):
        """A justificacion solicitud should be creatable."""
        solicitud = SolicitudFactory(
            tipo=Solicitud.TipoSolicitud.JUSTIFICACION,
        )
        assert solicitud.tipo == "justificacion"
