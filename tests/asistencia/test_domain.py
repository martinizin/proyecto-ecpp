"""
Unit tests for AsistenciaCalculoService — Pure Python, no DB required.
Tests: percentage calculations, edge cases, risk evaluation (HU10).
"""

from decimal import Decimal

import pytest

from apps.asistencia.domain.services import AsistenciaCalculoService


class TestAsistenciaCalculoService:
    """Tests for attendance percentage calculation service."""

    def setup_method(self):
        self.service = AsistenciaCalculoService()

    # --- calcular_porcentaje_asistencia ---

    def test_porcentaje_asistencia_todas_presentes(self):
        assert self.service.calcular_porcentaje_asistencia(20, 20) == Decimal("100.00")

    def test_porcentaje_asistencia_todas_ausentes(self):
        assert self.service.calcular_porcentaje_asistencia(0, 20) == Decimal("0.00")

    def test_porcentaje_asistencia_parcial(self):
        assert self.service.calcular_porcentaje_asistencia(15, 20) == Decimal("75.00")

    def test_porcentaje_asistencia_sin_sesiones(self):
        """0 sesiones = 100% asistencia (0% inasistencia)."""
        assert self.service.calcular_porcentaje_asistencia(0, 0) == Decimal("100.00")

    def test_porcentaje_asistencia_redondeo(self):
        """1/3 = 33.33%."""
        result = self.service.calcular_porcentaje_asistencia(1, 3)
        assert result == Decimal("33.33")

    @pytest.mark.parametrize(
        "asistidas, total, esperado",
        [
            (19, 20, Decimal("95.00")),
            (18, 20, Decimal("90.00")),
            (1, 20, Decimal("5.00")),
            (7, 10, Decimal("70.00")),
            (99, 100, Decimal("99.00")),
        ],
    )
    def test_porcentaje_asistencia_parametrizado(self, asistidas, total, esperado):
        assert self.service.calcular_porcentaje_asistencia(asistidas, total) == esperado

    # --- calcular_porcentaje_inasistencia ---

    def test_porcentaje_inasistencia_todas_presentes(self):
        assert self.service.calcular_porcentaje_inasistencia(20, 20) == Decimal("0.00")

    def test_porcentaje_inasistencia_todas_ausentes(self):
        assert self.service.calcular_porcentaje_inasistencia(0, 20) == Decimal("100.00")

    def test_porcentaje_inasistencia_parcial(self):
        assert self.service.calcular_porcentaje_inasistencia(19, 20) == Decimal("5.00")

    def test_porcentaje_inasistencia_sin_sesiones(self):
        assert self.service.calcular_porcentaje_inasistencia(0, 0) == Decimal("0.00")

    # --- calcular_porcentaje_general ---

    def test_porcentaje_general_multiples_asignaturas(self):
        datos = [
            {"sesiones_asistidas": 18, "total_sesiones": 20},
            {"sesiones_asistidas": 10, "total_sesiones": 10},
        ]
        # (18+10)/(20+10) = 28/30 = 93.33%
        assert self.service.calcular_porcentaje_general(datos) == Decimal("93.33")

    def test_porcentaje_general_lista_vacia(self):
        assert self.service.calcular_porcentaje_general([]) == Decimal("100.00")

    def test_porcentaje_general_una_asignatura(self):
        datos = [{"sesiones_asistidas": 15, "total_sesiones": 20}]
        assert self.service.calcular_porcentaje_general(datos) == Decimal("75.00")

    def test_porcentaje_general_todas_perfectas(self):
        datos = [
            {"sesiones_asistidas": 20, "total_sesiones": 20},
            {"sesiones_asistidas": 15, "total_sesiones": 15},
        ]
        assert self.service.calcular_porcentaje_general(datos) == Decimal("100.00")

    # --- calcular_inasistencia_general ---

    def test_inasistencia_general(self):
        datos = [
            {"sesiones_asistidas": 18, "total_sesiones": 20},
            {"sesiones_asistidas": 10, "total_sesiones": 10},
        ]
        # 100 - 93.33 = 6.67%
        assert self.service.calcular_inasistencia_general(datos) == Decimal("6.67")

    # --- evaluar_riesgo ---

    def test_riesgo_verde_por_debajo_umbral(self):
        assert self.service.evaluar_riesgo(Decimal("4.99")) == "verde"

    def test_riesgo_verde_cero(self):
        assert self.service.evaluar_riesgo(Decimal("0.00")) == "verde"

    def test_riesgo_rojo_exacto_umbral(self):
        assert self.service.evaluar_riesgo(Decimal("5.00")) == "rojo"

    def test_riesgo_rojo_por_encima_umbral(self):
        assert self.service.evaluar_riesgo(Decimal("10.00")) == "rojo"

    def test_riesgo_rojo_100_porciento(self):
        assert self.service.evaluar_riesgo(Decimal("100.00")) == "rojo"

    @pytest.mark.parametrize(
        "porcentaje, esperado",
        [
            (Decimal("0.00"), "verde"),
            (Decimal("4.99"), "verde"),
            (Decimal("5.00"), "rojo"),
            (Decimal("5.01"), "rojo"),
            (Decimal("50.00"), "rojo"),
        ],
    )
    def test_evaluar_riesgo_parametrizado(self, porcentaje, esperado):
        assert self.service.evaluar_riesgo(porcentaje) == esperado
