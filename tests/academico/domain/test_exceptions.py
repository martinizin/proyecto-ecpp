"""
Pruebas unitarias para las nuevas excepciones de dominio (HU21 QA V1-V4).

Verifican que cada excepción:
- Hereda de la base AcademicoError.
- Expone los atributos de contexto requeridos.
- Produce un mensaje en español que incluye los valores numéricos clave.
"""

import pytest

from apps.academico.domain.exceptions import (
    AcademicoError,
    CapacidadParaleloInvalidaError,
    DuracionPeriodoInvalidaError,
    HorasLectivasInvalidasError,
    MaxAsignaturasExcedidasError,
)


class TestHorasLectivasInvalidasError:
    def test_hereda_de_academico_error(self):
        assert issubclass(HorasLectivasInvalidasError, AcademicoError)

    def test_expone_atributos_y_mensaje(self):
        exc = HorasLectivasInvalidasError(horas=80, maximo=60)

        assert exc.horas == 80
        assert exc.maximo == 60
        msg = str(exc)
        assert "80" in msg
        assert "60" in msg


class TestCapacidadParaleloInvalidaError:
    def test_hereda_de_academico_error(self):
        assert issubclass(CapacidadParaleloInvalidaError, AcademicoError)

    def test_expone_atributos_y_mensaje(self):
        exc = CapacidadParaleloInvalidaError(capacidad=75, maximo=50)

        assert exc.capacidad == 75
        assert exc.maximo == 50
        msg = str(exc)
        assert "75" in msg
        assert "50" in msg


class TestDuracionPeriodoInvalidaError:
    def test_hereda_de_academico_error(self):
        assert issubclass(DuracionPeriodoInvalidaError, AcademicoError)

    def test_expone_atributos_y_mensaje(self):
        exc = DuracionPeriodoInvalidaError(meses=3, minimo=4, maximo=7)

        assert exc.meses == 3
        assert exc.minimo == 4
        assert exc.maximo == 7
        msg = str(exc)
        assert "3" in msg
        assert "4" in msg
        assert "7" in msg


class TestMaxAsignaturasExcedidasError:
    def test_hereda_de_academico_error(self):
        assert issubclass(MaxAsignaturasExcedidasError, AcademicoError)

    def test_expone_atributos_y_mensaje(self):
        exc = MaxAsignaturasExcedidasError(
            actual=6, limite=5, tipo_licencia_codigo="BASICA"
        )

        assert exc.actual == 6
        assert exc.limite == 5
        assert exc.tipo_licencia_codigo == "BASICA"
        msg = str(exc)
        assert "6" in msg
        assert "5" in msg
        assert "BASICA" in msg
