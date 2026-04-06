"""Tests for Asistencia model."""

import datetime

import pytest
from django.db import IntegrityError

from apps.asistencia.infrastructure.models import Asistencia
from tests.factories import AsistenciaFactory


pytestmark = pytest.mark.django_db


class TestAsistencia:
    """Tests for Asistencia model."""

    def test_create_asistencia(self):
        asistencia = AsistenciaFactory()
        assert asistencia.pk is not None
        assert asistencia.estado == Asistencia.Estado.PRESENTE
        assert asistencia.estudiante.rol == "estudiante"

    def test_str(self):
        asistencia = AsistenciaFactory()
        expected = (
            f"{asistencia.estudiante} - {asistencia.fecha} "
            f"({asistencia.get_estado_display()})"
        )
        assert str(asistencia) == expected

    def test_estado_choices(self):
        """Three attendance states should be defined."""
        choices = [c[0] for c in Asistencia.Estado.choices]
        assert "presente" in choices
        assert "ausente" in choices
        assert "justificado" in choices
        assert len(choices) == 3

    def test_unique_together_estudiante_paralelo_fecha(self):
        """Same estudiante + paralelo + fecha should be rejected."""
        asistencia = AsistenciaFactory(fecha=datetime.date(2026, 5, 1))
        with pytest.raises(IntegrityError):
            AsistenciaFactory(
                estudiante=asistencia.estudiante,
                paralelo=asistencia.paralelo,
                fecha=datetime.date(2026, 5, 1),
            )

    def test_different_fecha_allowed(self):
        """Same estudiante + paralelo but different fecha is allowed."""
        asistencia = AsistenciaFactory(fecha=datetime.date(2026, 5, 1))
        asistencia2 = AsistenciaFactory(
            estudiante=asistencia.estudiante,
            paralelo=asistencia.paralelo,
            fecha=datetime.date(2026, 5, 2),
        )
        assert asistencia2.pk is not None
        assert asistencia2.pk != asistencia.pk

    def test_default_estado_presente(self):
        """Default estado should be 'presente'."""
        asistencia = AsistenciaFactory()
        assert asistencia.estado == "presente"
