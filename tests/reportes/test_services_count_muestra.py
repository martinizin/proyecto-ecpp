"""
Tests para ``obtener_count_y_muestra()`` en los 2 export services (HU27b WU2).

Método puro de orquestación, sin generar archivos. Reusa los helpers
internos de cada service (que ya delegan al domain service de cálculo).

Refs:
- Spec R25 (service reuse contract): el método NO re-implementa la
  fórmula; delega a ``CalificacionValidationService`` /
  ``AsistenciaCalculoService``.
- Design §4.7 (contract): retorna ``(int, list[dict])``.
- WU1 (PreviewExportView): el método reemplaza la lógica inlineada en
  la view; las keys del sample deben coincidir para que la refactor
  sea transparente.
"""

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.asistencia.domain.services import AsistenciaCalculoService
from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.domain.services import CalificacionValidationService
from apps.reportes.application.services import (
    ExportacionAsistenciaService,
    ExportacionCalificacionesService,
)
from tests.factories import (
    AsistenciaFactory,
    CalificacionFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _crear_paralelo_con_notas(periodo=None, num_estudiantes=5):
    """Crea un paralelo con N estudiantes activos y 3 evaluaciones registradas."""
    periodo = periodo or PeriodoFactory(nombre="2026-A")
    paralelo = ParaleloFactory(periodo=periodo, nombre="A")
    RegistroCalificacionParaleloFactory(paralelo=paralelo)
    evaluaciones = []
    for tipo, peso in [
        ("parcial1", Decimal("30.00")),
        ("parcial2_10h", Decimal("30.00")),
        ("examen_final", Decimal("40.00")),
    ]:
        ev = EvaluacionFactory(paralelo=paralelo, tipo=tipo, peso=peso)
        evaluaciones.append(ev)
    for _ in range(num_estudiantes):
        matricula = MatriculaFactory(paralelo=paralelo)
        for ev in evaluaciones:
            CalificacionFactory(
                evaluacion=ev,
                estudiante=matricula.estudiante,
                nota=Decimal("15.00"),
            )
    return periodo, paralelo


def _crear_paralelo_con_asistencia(periodo=None, num_estudiantes=5):
    """Crea un paralelo con N estudiantes y 10 sesiones de asistencia variadas.

    Patrón: 8 presente, 1 ausente, 1 justificado = 90% asistencia.
    """
    periodo = periodo or PeriodoFactory(nombre="2026-A")
    paralelo = ParaleloFactory(periodo=periodo, nombre="A")
    for _ in range(num_estudiantes):
        matricula = MatriculaFactory(paralelo=paralelo)
        for d in range(1, 11):
            estado = (
                Asistencia.Estado.PRESENTE
                if d < 9
                else (Asistencia.Estado.AUSENTE if d == 9 else Asistencia.Estado.JUSTIFICADO)
            )
            AsistenciaFactory(
                estudiante=matricula.estudiante,
                paralelo=paralelo,
                fecha=datetime.date(2026, 4, d),
                estado=estado,
            )
    return periodo, paralelo


# ---------------------------------------------------------------------------
# Calificaciones
# ---------------------------------------------------------------------------


class TestObtenerCountYMuestraCalificaciones:
    """``ExportacionCalificacionesService.obtener_count_y_muestra()`` (HU27b WU2)."""

    def test_obtener_count_y_muestra_calificaciones_retorna_count_y_3_filas(self, docente):
        """Paralelo con 5 estudiantes → (5, [3 dicts])."""
        periodo, paralelo = _crear_paralelo_con_notas(num_estudiantes=5)
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id, "paralelo_id": paralelo.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 5
        assert len(sample_rows) == 3
        for fila in sample_rows:
            assert "cedula" in fila
            assert "nombres" in fila
            assert "promedio" in fila
            assert "estado" in fila

    def test_obtener_count_y_muestra_calificaciones_filtra_por_paralelo(self, docente):
        """Con 2 paralelos, el filtro ``paralelo_id`` limita el count al paralelo elegido."""
        periodo = PeriodoFactory(nombre="2026-A")
        p1 = ParaleloFactory(periodo=periodo, nombre="A")
        ParaleloFactory(periodo=periodo, nombre="B")
        RegistroCalificacionParaleloFactory(paralelo=p1)
        ev = EvaluacionFactory(paralelo=p1, tipo="parcial1", peso=Decimal("100.00"))
        for _ in range(3):
            m = MatriculaFactory(paralelo=p1)
            CalificacionFactory(evaluacion=ev, estudiante=m.estudiante, nota=Decimal("16.00"))

        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id, "paralelo_id": p1.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 3
        assert len(sample_rows) == 3

    def test_obtener_count_y_muestra_calificaciones_retorna_vacio_si_sin_resultados(self, docente):
        """Filtros sin paralelos → ``(0, [])``."""
        periodo = PeriodoFactory(nombre="2026-A")
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 0
        assert sample_rows == []

    def test_obtener_count_y_muestra_calificaciones_delega_a_validation_service(self, docente):
        """El cálculo del estado delega a ``CalificacionValidationService.estado_aprobacion``.

        R25: no se re-implementa la fórmula; se delega.
        """
        periodo, paralelo = _crear_paralelo_con_notas(num_estudiantes=1)
        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id, "paralelo_id": paralelo.id},
            usuario=docente,
        )

        with patch.object(
            CalificacionValidationService,
            "estado_aprobacion",
            wraps=CalificacionValidationService.estado_aprobacion,
        ) as spy:
            count, sample_rows = service.obtener_count_y_muestra()

        assert count == 1
        assert len(sample_rows) == 1
        assert spy.called, (
            "El método debe delegar a CalificacionValidationService.estado_aprobacion "
            "(no re-implementar la fórmula)"
        )

    def test_obtener_count_y_muestra_calificaciones_sin_notas_estado_sin_notas(self, docente):
        """Sin notas: ``promedio`` es ``None`` y ``estado`` es ``sin_notas``."""
        periodo = PeriodoFactory(nombre="2026-A")
        paralelo = ParaleloFactory(periodo=periodo, nombre="A")
        RegistroCalificacionParaleloFactory(paralelo=paralelo)
        # Crear evaluaciones pero sin notas registradas
        for tipo, peso in [
            ("parcial1", Decimal("30.00")),
            ("parcial2_10h", Decimal("30.00")),
            ("examen_final", Decimal("40.00")),
        ]:
            EvaluacionFactory(paralelo=paralelo, tipo=tipo, peso=peso)
        MatriculaFactory(paralelo=paralelo)

        service = ExportacionCalificacionesService(
            filtros={"periodo_id": periodo.id, "paralelo_id": paralelo.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 1
        assert len(sample_rows) == 1
        fila = sample_rows[0]
        assert fila["promedio"] is None
        assert fila["estado"] == "sin_notas"


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------


class TestObtenerCountYMuestraAsistencia:
    """``ExportacionAsistenciaService.obtener_count_y_muestra()`` (HU27b WU2)."""

    def test_obtener_count_y_muestra_asistencia_retorna_count_y_3_filas(self, docente):
        """Paralelo con 5 estudiantes → ``(5, [3 dicts])``."""
        periodo, paralelo = _crear_paralelo_con_asistencia(num_estudiantes=5)
        service = ExportacionAsistenciaService(
            filtros={"periodo_id": periodo.id, "paralelo_id": paralelo.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 5
        assert len(sample_rows) == 3
        for fila in sample_rows:
            assert "cedula" in fila
            assert "nombres" in fila
            assert "porcentaje_asistencia" in fila
            assert "estado" in fila

    def test_obtener_count_y_muestra_asistencia_calcula_porcentaje(self, docente):
        """El ``porcentaje_asistencia`` se calcula vía ``AsistenciaCalculoService``.

        Setup: 1 estudiante, 10 sesiones (8 presente + 1 ausente + 1 justificado)
        → asistencia = (8+1)/10 = 90.00%.

        Spy via ``side_effect``: ``calcular_porcentaje_asistencia`` es instance
        method, pero ``patch.object`` no preserva el descriptor protocol — el
        ``side_effect`` recibe solo los args explícitos (sin ``self``).
        """
        periodo, paralelo = _crear_paralelo_con_asistencia(num_estudiantes=1)
        service = ExportacionAsistenciaService(
            filtros={"periodo_id": periodo.id, "paralelo_id": paralelo.id},
            usuario=docente,
        )

        # ``original`` es un bound method — instanciamos para evitar pasar ``self``.
        original = AsistenciaCalculoService().calcular_porcentaje_asistencia
        calls = []

        def spy_side_effect(sesiones_asistidas, total_sesiones):
            calls.append((sesiones_asistidas, total_sesiones))
            return original(sesiones_asistidas, total_sesiones)

        with patch.object(
            AsistenciaCalculoService,
            "calcular_porcentaje_asistencia",
            side_effect=spy_side_effect,
        ):
            count, sample_rows = service.obtener_count_y_muestra()

        assert count == 1
        assert len(sample_rows) == 1
        assert calls, (
            "El método debe delegar a AsistenciaCalculoService.calcular_porcentaje_asistencia "
            "(no re-implementar la fórmula)"
        )
        # 9 asistidas / 10 totales = 90.00%
        assert sample_rows[0]["porcentaje_asistencia"] == 90.00

    def test_obtener_count_y_muestra_asistencia_retorna_vacio_si_sin_resultados(self, docente):
        """Filtros sin paralelos → ``(0, [])``."""
        periodo = PeriodoFactory(nombre="2026-A")
        service = ExportacionAsistenciaService(
            filtros={"periodo_id": periodo.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 0
        assert sample_rows == []

    def test_obtener_count_y_muestra_asistencia_filtra_por_paralelo(self, docente):
        """Con 2 paralelos, el filtro ``paralelo_id`` limita el count al paralelo elegido."""
        periodo = PeriodoFactory(nombre="2026-A")
        p1 = ParaleloFactory(periodo=periodo, nombre="A")
        ParaleloFactory(periodo=periodo, nombre="B")
        for _ in range(2):
            m = MatriculaFactory(paralelo=p1)
            for d in range(1, 11):
                AsistenciaFactory(
                    estudiante=m.estudiante,
                    paralelo=p1,
                    fecha=datetime.date(2026, 4, d),
                    estado=Asistencia.Estado.PRESENTE,
                )

        service = ExportacionAsistenciaService(
            filtros={"periodo_id": periodo.id, "paralelo_id": p1.id},
            usuario=docente,
        )

        count, sample_rows = service.obtener_count_y_muestra()

        assert count == 2
        assert len(sample_rows) == 2
