"""Tests for Periodo, Asignatura, and Paralelo models."""

import datetime

import pytest
from django.db import IntegrityError

from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo
from tests.factories import (
    AsignaturaFactory,
    DocenteFactory,
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
