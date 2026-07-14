"""Tests for Evaluacion, Calificacion and sub-nota (HU32) models."""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.calificaciones.infrastructure.models import Evaluacion
from tests.factories import (
    CalificacionFactory,
    ConfiguracionSubNotasFactory,
    EvaluacionFactory,
    SubNotaConfigFactory,
    SubNotaParcialFactory,
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
            f"{calificacion.estudiante} - {calificacion.evaluacion}: " f"{calificacion.nota}"
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


class TestEvaluacionEsParcial:
    """Tests for Evaluacion.es_parcial property (HU32)."""

    @pytest.mark.parametrize(
        "tipo",
        [
            Evaluacion.TipoEvaluacion.PARCIAL_1,
            Evaluacion.TipoEvaluacion.PARCIAL_2_10H,
            Evaluacion.TipoEvaluacion.PARCIAL_3,
            Evaluacion.TipoEvaluacion.PARCIAL_4_10H,
        ],
    )
    def test_parciales_admiten_sub_notas(self, tipo):
        evaluacion = EvaluacionFactory(tipo=tipo)
        assert evaluacion.es_parcial is True

    @pytest.mark.parametrize(
        "tipo",
        [
            Evaluacion.TipoEvaluacion.PROYECTO,
            Evaluacion.TipoEvaluacion.EXAMEN_FINAL,
        ],
    )
    def test_proyecto_y_examen_no_admiten_sub_notas(self, tipo):
        evaluacion = EvaluacionFactory(tipo=tipo)
        assert evaluacion.es_parcial is False


class TestConfiguracionSubNotas:
    """Tests for ConfiguracionSubNotas and SubNotaConfig models (HU32)."""

    def test_create_configuracion(self):
        config = ConfiguracionSubNotasFactory()
        assert config.pk is not None
        assert config.creado_en is not None

    def test_una_configuracion_por_evaluacion(self):
        """OneToOne: una sola configuración por evaluación."""
        config = ConfiguracionSubNotasFactory()
        with pytest.raises(IntegrityError):
            ConfiguracionSubNotasFactory(evaluacion=config.evaluacion)

    def test_items_con_nombre_y_orden(self):
        config = ConfiguracionSubNotasFactory()
        item1 = SubNotaConfigFactory(configuracion=config, nombre="Tarea 1", orden=1)
        item2 = SubNotaConfigFactory(configuracion=config, nombre="Quiz", orden=2)
        assert list(config.items.all()) == [item1, item2]
        assert str(item1) == "1. Tarea 1"
        assert str(item2) == "2. Quiz"

    def test_orden_unico_por_configuracion(self):
        config = ConfiguracionSubNotasFactory()
        SubNotaConfigFactory(configuracion=config, orden=1)
        with pytest.raises(IntegrityError):
            SubNotaConfigFactory(configuracion=config, orden=1)


class TestSubNotaParcial:
    """Tests for SubNotaParcial model (HU32)."""

    def test_create_sub_nota(self):
        sub_nota = SubNotaParcialFactory(nombre="Tarea 1", nota=Decimal("18.50"), orden=1)
        assert sub_nota.pk is not None
        assert sub_nota.nota == Decimal("18.50")
        assert sub_nota.nota_final_parcial_override is None
        assert sub_nota.justificacion_override == ""

    def test_str(self):
        sub_nota = SubNotaParcialFactory(nombre="Quiz", nota=Decimal("15.00"), orden=1)
        expected = (
            f"{sub_nota.matricula.estudiante} — {sub_nota.evaluacion} — " f"Quiz: {sub_nota.nota}"
        )
        assert str(sub_nota) == expected

    def test_unique_evaluacion_matricula_orden(self):
        """No puede repetirse el orden para la misma evaluación y matrícula."""
        sub_nota = SubNotaParcialFactory(orden=1)
        with pytest.raises(IntegrityError):
            SubNotaParcialFactory(
                evaluacion=sub_nota.evaluacion,
                matricula=sub_nota.matricula,
                orden=1,
            )

    def test_check_constraint_nota_mayor_a_20(self):
        with pytest.raises(IntegrityError):
            SubNotaParcialFactory(nota=Decimal("20.01"))

    def test_sub_notas_de_un_estudiante_en_un_parcial(self):
        """Un estudiante puede tener 3-5 sub-notas en el mismo parcial."""
        sub_nota = SubNotaParcialFactory(orden=1)
        for orden in (2, 3):
            SubNotaParcialFactory(
                evaluacion=sub_nota.evaluacion,
                matricula=sub_nota.matricula,
                orden=orden,
            )
        total = sub_nota.evaluacion.sub_notas.filter(matricula=sub_nota.matricula).count()
        assert total == 3

    def test_override_con_justificacion(self):
        sub_nota = SubNotaParcialFactory(
            nota_final_parcial_override=Decimal("16.00"),
            justificacion_override="Se ajusta por participación destacada.",
        )
        assert sub_nota.nota_final_parcial_override == Decimal("16.00")
        assert sub_nota.justificacion_override != ""
