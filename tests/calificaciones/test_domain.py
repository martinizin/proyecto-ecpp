"""Tests for HU13: Nota VO and CalificacionValidationService."""

from decimal import Decimal

import pytest

from apps.calificaciones.domain.exceptions import (
    NotaFueraDeRangoError,
    PesosInvalidosError,
)
from apps.calificaciones.domain.services import CalificacionValidationService
from apps.calificaciones.domain.value_objects import Nota


# ---------------------------------------------------------------------------
# Nota VO
# ---------------------------------------------------------------------------


class TestNotaVO:
    """Tests for the Nota value object."""

    @pytest.mark.parametrize("valor", ["0", "5", "14", "16", "20"])
    def test_nota_entera_valida(self, valor):
        nota = Nota(valor=Decimal(valor))
        assert nota.valor == Decimal(valor)

    @pytest.mark.parametrize("valor", ["-1", "21", "25", "100"])
    def test_nota_fuera_de_rango(self, valor):
        with pytest.raises(NotaFueraDeRangoError):
            Nota(valor=Decimal(valor))

    @pytest.mark.parametrize("valor", ["15.50", "16.99", "0.01", "19.99"])
    def test_nota_con_decimal_valida(self, valor):
        """PRD: escala 0.00–20.00 con 2 decimales — los decimales deben aceptarse."""
        nota = Nota(valor=Decimal(valor))
        assert nota.valor == Decimal(valor)

    def test_nota_aprobado_en_limite(self):
        assert Nota(valor=Decimal("16")).aprobado is True

    def test_nota_reprobado_justo_abajo(self):
        assert Nota(valor=Decimal("15")).aprobado is False

    def test_nota_cero_reprobado(self):
        assert Nota(valor=Decimal("0")).aprobado is False

    def test_nota_maxima_aprobado(self):
        assert Nota(valor=Decimal("20")).aprobado is True

    def test_nota_frozen(self):
        """Nota es inmutable — no debe permitir reasignación."""
        nota = Nota(valor=Decimal("10"))
        with pytest.raises(Exception):
            nota.valor = Decimal("5")

    def test_nota_str_muestra_dos_decimales(self):
        """__str__ debe mostrar siempre 2 decimales para consistencia."""
        assert str(Nota(valor=Decimal("15"))) == "15.00"
        assert str(Nota(valor=Decimal("17.50"))) == "17.50"
        assert str(Nota(valor=Decimal("0"))) == "0.00"

    def test_nota_igualdad(self):
        assert Nota(valor=Decimal("10")) == Nota(valor=Decimal("10"))

    def test_nota_desigualdad(self):
        assert Nota(valor=Decimal("10")) != Nota(valor=Decimal("11"))


# ---------------------------------------------------------------------------
# CalificacionValidationService
# ---------------------------------------------------------------------------


class TestCalificacionValidationService:
    """Tests for CalificacionValidationService."""

    def test_validar_nota_entera_valida(self):
        nota = CalificacionValidationService.validar_nota("16")
        assert isinstance(nota, Nota)
        assert nota.valor == Decimal("16")

    def test_validar_nota_fuera_de_rango(self):
        with pytest.raises(NotaFueraDeRangoError):
            CalificacionValidationService.validar_nota("21")

    def test_validar_nota_decimal_valida(self):
        """PRD: escala 0.00–20.00 — el servicio debe aceptar decimales."""
        nota = CalificacionValidationService.validar_nota("15.50")
        assert nota.valor == Decimal("15.50")

    @pytest.mark.parametrize(
        "pesos",
        [
            {"parcial1": Decimal("25"), "parcial2": Decimal("25"), "parcial3": Decimal("50")},
            {"examen": Decimal("100")},
            {
                "p1": Decimal("25"),
                "p2": Decimal("25"),
                "p3": Decimal("25"),
                "p4": Decimal("25"),
            },
        ],
    )
    def test_pesos_validos(self, pesos):
        CalificacionValidationService.validar_pesos_evaluaciones(pesos)  # no exception

    @pytest.mark.parametrize(
        "pesos",
        [
            {"parcial1": Decimal("40"), "parcial2": Decimal("40")},
            {"p1": Decimal("0")},
            {"p1": Decimal("50"), "p2": Decimal("60")},
        ],
    )
    def test_pesos_invalidos(self, pesos):
        with pytest.raises(PesosInvalidosError):
            CalificacionValidationService.validar_pesos_evaluaciones(pesos)

    def test_promedio_ponderado_simple(self):
        notas = [
            (Decimal("20"), Decimal("50")),
            (Decimal("10"), Decimal("50")),
        ]
        resultado = CalificacionValidationService.calcular_promedio_ponderado(notas)
        assert resultado == Decimal("15.00")

    def test_promedio_ponderado_asimetrico(self):
        notas = [
            (Decimal("18"), Decimal("75")),
            (Decimal("10"), Decimal("25")),
        ]
        resultado = CalificacionValidationService.calcular_promedio_ponderado(notas)
        assert resultado == Decimal("16.00")

    def test_promedio_ponderado_notas_iguales(self):
        """Dos evaluaciones con la misma nota no deben colisionar."""
        notas = [
            (Decimal("15"), Decimal("50")),
            (Decimal("15"), Decimal("50")),
        ]
        resultado = CalificacionValidationService.calcular_promedio_ponderado(notas)
        assert resultado == Decimal("15.00")

    def test_promedio_ponderado_vacio(self):
        resultado = CalificacionValidationService.calcular_promedio_ponderado([])
        assert resultado == Decimal("0.00")

    @pytest.mark.parametrize(
        "promedio,esperado",
        [
            (Decimal("16"), "aprobado"),
            (Decimal("20"), "aprobado"),
            (Decimal("15"), "reprobado"),
            (Decimal("0"), "reprobado"),
        ],
    )
    def test_estado_aprobacion(self, promedio, esperado):
        assert CalificacionValidationService.estado_aprobacion(promedio) == esperado
