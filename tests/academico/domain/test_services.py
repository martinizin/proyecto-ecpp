"""
Unit tests for domain services in the Academico bounded context.

Tests validate pure-Python domain rules (no Django imports, no DB).
"""

from datetime import date

import pytest

from apps.academico.domain.exceptions import (
    CapacidadParaleloInvalidaError,
    DuracionPeriodoInvalidaError,
    HorasLectivasInvalidasError,
)
from apps.academico.domain.services import AsignaturaService, ParaleloService, PeriodoService


class TestAsignaturaServiceValidarHorasLectivas:
    """Test validar_horas_lectivas boundary scenarios per design §5 V2."""

    def test_v2_1_horas_1_es_valida(self):
        """V2#1: horas=1 → passes (minimum valid)."""
        service = AsignaturaService()
        # Should not raise
        service.validar_horas_lectivas(horas=1)

    def test_v2_2_horas_0_levanta_excepcion(self):
        """V2#2: horas=0 → raises HorasLectivasInvalidasError."""
        service = AsignaturaService()
        with pytest.raises(HorasLectivasInvalidasError) as exc_info:
            service.validar_horas_lectivas(horas=0)

        assert exc_info.value.horas == 0
        assert exc_info.value.maximo == 60
        assert "entre 1 y 60" in str(exc_info.value)

    def test_v2_3_horas_60_es_valida(self):
        """V2#3: horas=60 → passes (maximum valid)."""
        service = AsignaturaService()
        # Should not raise
        service.validar_horas_lectivas(horas=60)

    def test_v2_4_horas_61_levanta_excepcion(self):
        """V2#4: horas=61 → raises, message contains 'entre 1 y 60'."""
        service = AsignaturaService()
        with pytest.raises(HorasLectivasInvalidasError) as exc_info:
            service.validar_horas_lectivas(horas=61)

        assert exc_info.value.horas == 61
        assert exc_info.value.maximo == 60
        assert "entre 1 y 60" in str(exc_info.value)

    def test_v2_5_horas_negativa_levanta_excepcion(self):
        """V2#5: horas=-3 → raises."""
        service = AsignaturaService()
        with pytest.raises(HorasLectivasInvalidasError) as exc_info:
            service.validar_horas_lectivas(horas=-3)

        assert exc_info.value.horas == -3
        assert exc_info.value.maximo == 60


class TestParaleloServiceValidarCapacidad:
    """Test validar_capacidad boundary scenarios per design §5 V3."""

    def test_v3_1_capacidad_1_es_valida(self):
        """V3#1: capacidad=1, maximo=50 → passes (minimum valid)."""
        service = ParaleloService()
        # Should not raise
        service.validar_capacidad(capacidad=1, maximo=50)

    def test_v3_2_capacidad_0_levanta_excepcion(self):
        """V3#2: capacidad=0, maximo=50 → raises CapacidadParaleloInvalidaError."""
        service = ParaleloService()
        with pytest.raises(CapacidadParaleloInvalidaError) as exc_info:
            service.validar_capacidad(capacidad=0, maximo=50)

        assert exc_info.value.capacidad == 0
        assert exc_info.value.maximo == 50

    def test_v3_3_capacidad_50_es_valida(self):
        """V3#3: capacidad=50, maximo=50 → passes (maximum valid)."""
        service = ParaleloService()
        # Should not raise
        service.validar_capacidad(capacidad=50, maximo=50)

    def test_v3_4_capacidad_51_levanta_excepcion(self):
        """V3#4: capacidad=51, maximo=50 → raises, message contains 'entre 1 y 50'."""
        service = ParaleloService()
        with pytest.raises(CapacidadParaleloInvalidaError) as exc_info:
            service.validar_capacidad(capacidad=51, maximo=50)

        assert exc_info.value.capacidad == 51
        assert exc_info.value.maximo == 50
        assert "entre 1 y 50" in str(exc_info.value)


class TestPeriodoServiceValidarDuracion:
    """Test validar_duracion boundary scenarios per design §5 V4 (lenient months)."""

    def test_v4_1_exacto_4_meses_es_valido(self):
        """V4#1: 2026-01-01 → 2026-05-01 (delta years=0 months=4 days=0) → total=4 → VALID."""
        service = PeriodoService()
        # Should not raise
        service.validar_duracion(
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 5, 1),
            minimo=4,
            maximo=7,
        )

    def test_v4_2_lenient_bump_a_4_meses_es_valido(self):
        """V4#2: 2026-01-01 → 2026-04-29 (3 months + 28 days) → lenient bump → total=4 → VALID."""
        service = PeriodoService()
        # Should not raise
        service.validar_duracion(
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 4, 29),
            minimo=4,
            maximo=7,
        )

    def test_v4_3_exacto_3_meses_levanta_excepcion(self):
        """V4#3: 2026-01-01 → 2026-04-01 (3 months, 0 days) → total=3 → INVALID."""
        service = PeriodoService()
        with pytest.raises(DuracionPeriodoInvalidaError) as exc_info:
            service.validar_duracion(
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 4, 1),
                minimo=4,
                maximo=7,
            )
        assert exc_info.value.meses == 3
        assert exc_info.value.minimo == 4
        assert exc_info.value.maximo == 7
        assert "entre 4 y 7 meses" in str(exc_info.value)

    def test_v4_4_exacto_7_meses_es_valido(self):
        """V4#4: 2026-01-01 → 2026-08-01 (7 months, 0 days) → total=7 → VALID."""
        service = PeriodoService()
        # Should not raise
        service.validar_duracion(
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 8, 1),
            minimo=4,
            maximo=7,
        )

    def test_v4_5_lenient_bump_a_8_meses_levanta_excepcion(self):
        """V4#5: 2026-01-01 → 2026-08-02 (7 months + 1 day) → lenient bump → total=8 → INVALID."""
        service = PeriodoService()
        with pytest.raises(DuracionPeriodoInvalidaError) as exc_info:
            service.validar_duracion(
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 8, 2),
                minimo=4,
                maximo=7,
            )
        assert exc_info.value.meses == 8
        assert exc_info.value.minimo == 4
        assert exc_info.value.maximo == 7
