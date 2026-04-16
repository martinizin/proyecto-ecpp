"""Tests for Periodo, Asignatura, Paralelo, and Matricula models."""

import datetime

import pytest
from django.db import IntegrityError

from apps.academico.infrastructure.models import Asignatura, Matricula, Paralelo, Periodo
from tests.factories import (
    AsignaturaFactory,
    DocenteFactory,
    EstudianteFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
)


pytestmark = pytest.mark.django_db


class TestPeriodo:
    """Tests for Periodo model."""

    def test_create_periodo(self):
        periodo = PeriodoFactory()
        assert periodo.pk is not None
        assert periodo.activo is True
        assert periodo.fecha_inicio == datetime.date(2026, 3, 1)

    def test_nombre_unique(self):
        PeriodoFactory(nombre="2026-1")
        with pytest.raises(IntegrityError):
            PeriodoFactory(nombre="2026-1")

    def test_str(self):
        periodo = PeriodoFactory(nombre="2026-1")
        assert str(periodo) == "2026-1"

    def test_ordering_by_fecha_inicio_desc(self):
        """Periods should be ordered by fecha_inicio descending."""
        p1 = PeriodoFactory(
            nombre="A",
            fecha_inicio=datetime.date(2026, 1, 1),
            fecha_fin=datetime.date(2026, 6, 30),
        )
        p2 = PeriodoFactory(
            nombre="B",
            fecha_inicio=datetime.date(2026, 7, 1),
            fecha_fin=datetime.date(2026, 12, 31),
        )
        periodos = list(Periodo.objects.all())
        assert periodos[0] == p2
        assert periodos[1] == p1


class TestAsignatura:
    """Tests for Asignatura model."""

    def test_create_asignatura(self):
        asig = AsignaturaFactory()
        assert asig.pk is not None
        assert asig.descripcion == "Descripcion de prueba"

    def test_codigo_unique(self):
        AsignaturaFactory(codigo="MAT-001")
        with pytest.raises(IntegrityError):
            AsignaturaFactory(codigo="MAT-001")

    def test_str(self):
        asig = AsignaturaFactory(codigo="MAT-101", nombre="Matematicas I")
        assert str(asig) == "MAT-101 - Matematicas I"

    def test_ordering_by_codigo(self):
        a2 = AsignaturaFactory(codigo="ZZZ-001")
        a1 = AsignaturaFactory(codigo="AAA-001")
        asignaturas = list(Asignatura.objects.all())
        assert asignaturas[0] == a1
        assert asignaturas[1] == a2


class TestParalelo:
    """Tests for Paralelo model."""

    def test_create_paralelo(self):
        paralelo = ParaleloFactory()
        assert paralelo.pk is not None
        assert paralelo.docente.rol == "docente"

    def test_str(self):
        paralelo = ParaleloFactory()
        expected = (
            f"{paralelo.asignatura.codigo} - {paralelo.nombre} ({paralelo.periodo})"
        )
        assert str(paralelo) == expected

    def test_unique_together(self):
        """Same periodo + tipo_licencia + asignatura + nombre should be rejected."""
        paralelo = ParaleloFactory(nombre="A")
        with pytest.raises(IntegrityError):
            ParaleloFactory(
                asignatura=paralelo.asignatura,
                periodo=paralelo.periodo,
                tipo_licencia=paralelo.tipo_licencia,
                nombre="A",
            )

    def test_docente_limit_choices_to(self):
        """Paralelo should reference a docente user."""
        paralelo = ParaleloFactory()
        assert paralelo.docente.rol == "docente"


class TestMatricula:
    """Tests for Matricula model."""

    def test_create_matricula(self):
        matricula = MatriculaFactory()
        assert matricula.pk is not None
        assert matricula.estado == Matricula.Estado.ACTIVA
        assert matricula.estudiante.rol == "estudiante"

    def test_str(self):
        matricula = MatriculaFactory()
        expected = (
            f"{matricula.estudiante.get_full_name()} — "
            f"{matricula.paralelo} ({matricula.get_estado_display()})"
        )
        assert str(matricula) == expected

    def test_unique_together_estudiante_paralelo(self):
        """Same student + paralelo should be rejected."""
        matricula = MatriculaFactory()
        with pytest.raises(IntegrityError):
            MatriculaFactory(
                estudiante=matricula.estudiante,
                paralelo=matricula.paralelo,
            )

    def test_estado_choices(self):
        """All three states should be valid."""
        paralelo = ParaleloFactory()
        for estado in [Matricula.Estado.ACTIVA, Matricula.Estado.RETIRADA, Matricula.Estado.SUSPENDIDA]:
            m = MatriculaFactory(paralelo=paralelo, estado=estado)
            assert m.estado == estado

    def test_fecha_matricula_auto_set(self):
        matricula = MatriculaFactory()
        assert matricula.fecha_matricula is not None

    def test_ordering_by_fecha_desc(self):
        """Most recent enrollment first."""
        m1 = MatriculaFactory()
        m2 = MatriculaFactory()
        matriculas = list(Matricula.objects.all())
        assert matriculas[0] == m2
        assert matriculas[1] == m1
