"""
Tests unitarios para ``ReportesDisponibilidadService`` (HU27b).

El servicio es responsable del filtrado role-aware de ``Periodo`` y
``Paralelo`` para el hub de reportes y el endpoint ``/reportes/preview/``.

Reglas de filtrado (D2 del design):
- ``docente``: solo períodos/paralelos donde enseña.
- ``inspector`` / ``secretaria``: todos los períodos/paralelos.
- ``estudiante``: sin acceso (no se llama al servicio; la vista rechaza antes).

Spec concern #2: el view delega al service; el service NO importa
``HttpResponse`` ni ``View`` (DDD layering).
"""

from inspect import getsource

import pytest

from apps.academico.infrastructure.models import Periodo
from apps.reportes.domain.services import ReportesDisponibilidadService
from tests.factories import (
    ParaleloFactory,
    PeriodoFactory,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _crear_periodo_con_paralelo_docente(docente, nombre_periodo, nombre_paralelo):
    """Crea un periodo con un paralelo asignado a ``docente``."""
    periodo = PeriodoFactory(nombre=nombre_periodo)
    ParaleloFactory(periodo=periodo, nombre=nombre_paralelo, docente=docente)
    return periodo


# ---------------------------------------------------------------------------
# obtener_periodos_disponibles
# ---------------------------------------------------------------------------


class TestObtenerPeriodosDisponibles:
    """Filtrado role-aware de períodos disponibles."""

    def test_docente_solo_sus_periodos(self, docente):
        """Docente ve solo los períodos donde tiene al menos un paralelo asignado."""
        p_mio = _crear_periodo_con_paralelo_docente(docente, "2026-Mio", "A")
        # Otro periodo sin paralelo del docente
        PeriodoFactory(nombre="2026-Otro")

        periodos = ReportesDisponibilidadService.obtener_periodos_disponibles(docente)
        ids = [p.id for p in periodos]
        assert p_mio.id in ids
        assert len(periodos) == 1, "Docente no debería ver periodos sin paralelos propios"

    def test_docente_con_multiples_periodos(self, docente):
        """Docente con paralelos en 2 periodos ve los 2."""
        p1 = _crear_periodo_con_paralelo_docente(docente, "2026-A", "A")
        p2 = _crear_periodo_con_paralelo_docente(docente, "2026-B", "A")
        PeriodoFactory(nombre="2026-SinDocente")

        periodos = ReportesDisponibilidadService.obtener_periodos_disponibles(docente)
        ids = {p.id for p in periodos}
        assert ids == {p1.id, p2.id}

    def test_inspector_ve_todos_los_periodos(self, inspector):
        """Inspector ve todos los períodos (sin filtrar)."""
        PeriodoFactory(nombre="2026-A")
        PeriodoFactory(nombre="2026-B")
        PeriodoFactory(nombre="2026-C")

        periodos = ReportesDisponibilidadService.obtener_periodos_disponibles(inspector)
        assert len(periodos) == Periodo.objects.count()

    def test_secretaria_ve_todos_los_periodos(self, secretaria):
        """Secretaria ve todos los períodos (sin filtrar)."""
        PeriodoFactory(nombre="2026-A")
        PeriodoFactory(nombre="2026-B")

        periodos = ReportesDisponibilidadService.obtener_periodos_disponibles(secretaria)
        assert len(periodos) == Periodo.objects.count()

    def test_docente_sin_paralelos_no_ve_periodos(self, docente):
        """Docente sin paralelos asignados no ve ningún periodo."""
        PeriodoFactory(nombre="2026-A")  # sin paralelo del docente
        PeriodoFactory(nombre="2026-B")

        periodos = ReportesDisponibilidadService.obtener_periodos_disponibles(docente)
        assert list(periodos) == []


# ---------------------------------------------------------------------------
# obtener_paralelos_disponibles
# ---------------------------------------------------------------------------


class TestObtenerParalelosDisponibles:
    """Filtrado role-aware de paralelos disponibles en un periodo."""

    def test_docente_solo_sus_paralelos(self, docente):
        """Docente ve solo los paralelos donde enseña en el periodo."""
        periodo = PeriodoFactory(nombre="2026-A")
        mi_paralelo = ParaleloFactory(periodo=periodo, nombre="Mio", docente=docente)
        ParaleloFactory(periodo=periodo, nombre="Otro")  # sin docente asignado

        paralelos = ReportesDisponibilidadService.obtener_paralelos_disponibles(docente, periodo)
        ids = [p.id for p in paralelos]
        assert mi_paralelo.id in ids
        assert len(paralelos) == 1

    def test_docente_en_periodo_distinto_a_otros_no_ve_ajenos(self, docente):
        """Docente no ve paralelos del periodo donde NO enseña."""
        periodo = PeriodoFactory(nombre="2026-A")
        ParaleloFactory(periodo=periodo, nombre="A")
        ParaleloFactory(periodo=periodo, nombre="B")

        paralelos = ReportesDisponibilidadService.obtener_paralelos_disponibles(docente, periodo)
        # Ninguno asignado a este docente
        assert list(paralelos) == []

    def test_inspector_ve_todos_los_paralelos_del_periodo(self, inspector):
        """Inspector ve todos los paralelos del periodo."""
        periodo = PeriodoFactory(nombre="2026-A")
        p1 = ParaleloFactory(periodo=periodo, nombre="A")
        p2 = ParaleloFactory(periodo=periodo, nombre="B")
        ParaleloFactory(periodo=PeriodoFactory(nombre="2026-B"), nombre="C")

        paralelos = ReportesDisponibilidadService.obtener_paralelos_disponibles(inspector, periodo)
        ids = {p.id for p in paralelos}
        assert ids == {p1.id, p2.id}

    def test_secretaria_ve_todos_los_paralelos_del_periodo(self, secretaria):
        """Secretaria ve todos los paralelos del periodo."""
        periodo = PeriodoFactory(nombre="2026-A")
        p1 = ParaleloFactory(periodo=periodo, nombre="A")
        p2 = ParaleloFactory(periodo=periodo, nombre="B")

        paralelos = ReportesDisponibilidadService.obtener_paralelos_disponibles(
            secretaria, periodo
        )
        ids = {p.id for p in paralelos}
        assert ids == {p1.id, p2.id}


# ---------------------------------------------------------------------------
# DDD layering guard
# ---------------------------------------------------------------------------


class TestDDDLayering:
    """El service no debe importar nada de la capa de presentation."""

    def test_service_source_does_not_import_view_or_response(self):
        """El módulo de domain NO importa ``HttpResponse``, ``View`` ni ``JsonResponse``."""
        from apps.reportes import domain

        source = getsource(domain.services)
        # Verificamos que NO haya imports prohibidos (no basta con la palabra suelta,
        # porque puede aparecer en docstrings o comentarios).
        forbidden_imports = [
            "from django.http",
            "from django.views",
            "import View",
        ]
        for forbidden in forbidden_imports:
            assert (
                forbidden not in source
            ), f"domain/services.py contiene el import prohibido: {forbidden!r}"
