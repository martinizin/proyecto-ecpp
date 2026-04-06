"""Tests for Evaluacion and Calificacion models."""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion
from tests.factories import (
    CalificacionFactory,
    EstudianteFactory,
    EvaluacionFactory,
)


pytestmark = pytest.mark.django_db


class TestEvaluacion:
    """Tests for Evaluacion model."""

    def test_create_evaluacion(self):
        evaluacion = EvaluacionFactory()
        assert evaluacion.pk is not None
        assert evaluacion.peso == Decimal("25.00")

    def test_tipo_choices(self):
        """All 6 evaluation types should be defined."""
        choices = [c[0] for c in Evaluacion.TipoEvaluacion.choices]
        assert "parcial1" in choices
        assert "parcial2_10h" in choices
        assert "parcial3" in choices
        assert "parcial4_10h" in choices
        assert "proyecto" in choices
        assert "examen_final" in choices
        assert len(choices) == 6

    def test_str(self):
        evaluacion = EvaluacionFactory()
        expected = f"{evaluacion.get_tipo_display()} - {evaluacion.paralelo}"
        assert str(evaluacion) == expected

    def test_unique_together_paralelo_tipo(self):
        """Same paralelo + tipo should be rejected."""
        evaluacion = EvaluacionFactory(tipo=Evaluacion.TipoEvaluacion.PARCIAL_1)
        with pytest.raises(IntegrityError):
            EvaluacionFactory(
                paralelo=evaluacion.paralelo,
                tipo=Evaluacion.TipoEvaluacion.PARCIAL_1,
            )


class TestCalificacion:
    """Tests for Calificacion model."""

    def test_create_calificacion(self):
        calificacion = CalificacionFactory()
        assert calificacion.pk is not None
        assert calificacion.nota == Decimal("8.50")
        assert calificacion.fecha_registro is not None

    def test_str(self):
        calificacion = CalificacionFactory()
        expected = (
            f"{calificacion.estudiante} - {calificacion.evaluacion}: "
            f"{calificacion.nota}"
        )
        assert str(calificacion) == expected

    def test_unique_together_evaluacion_estudiante(self):
        """Same evaluacion + estudiante should be rejected."""
        calificacion = CalificacionFactory()
        with pytest.raises(IntegrityError):
            CalificacionFactory(
                evaluacion=calificacion.evaluacion,
                estudiante=calificacion.estudiante,
            )

    def test_estudiante_is_student_role(self):
        """Calificacion should reference a student user."""
        calificacion = CalificacionFactory()
        assert calificacion.estudiante.rol == "estudiante"
