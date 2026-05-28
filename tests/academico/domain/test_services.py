"""
Unit tests for domain services in the Academico bounded context.

Tests validate pure-Python domain rules (no Django imports, no DB).
"""

import pytest

from apps.academico.domain.exceptions import HorasLectivasInvalidasError
from apps.academico.domain.services import AsignaturaService


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
