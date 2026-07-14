"""Tests for HU13: Nota VO and CalificacionValidationService.
Tests for HU32: SubNotaValidationService."""

from decimal import Decimal

import pytest

from apps.calificaciones.domain.exceptions import (
    NotaFueraDeRangoError,
    PesosInvalidosError,
    SubNotasFueraDeRangoError,
)
from apps.calificaciones.domain.services import (
    CalificacionValidationService,
    SubNotaValidationService,
)
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


# ---------------------------------------------------------------------------
# SubNotaValidationService (HU32)
# ---------------------------------------------------------------------------


class TestSubNotaValidationService:
    """Tests for SubNotaValidationService (HU32: sub-notas 3-5 por parcial)."""

    @pytest.mark.parametrize("cantidad", [3, 4, 5])
    def test_cantidad_valida(self, cantidad):
        SubNotaValidationService.validar_cantidad(cantidad)  # no exception

    @pytest.mark.parametrize("cantidad", [0, 1, 2, 6, 10])
    def test_cantidad_fuera_de_rango(self, cantidad):
        with pytest.raises(SubNotasFueraDeRangoError):
            SubNotaValidationService.validar_cantidad(cantidad)

    def test_cantidad_invalida_incluye_limites_en_mensaje(self):
        with pytest.raises(SubNotasFueraDeRangoError) as exc_info:
            SubNotaValidationService.validar_cantidad(2)
        assert exc_info.value.cantidad == 2
        assert exc_info.value.minimo == 3
        assert exc_info.value.maximo == 5

    def test_promedio_tres_sub_notas(self):
        notas = [Decimal("15"), Decimal("18"), Decimal("12")]
        resultado = SubNotaValidationService.calcular_nota_final_sub_notas(notas)
        assert resultado == Decimal("15.00")

    def test_promedio_con_decimales_redondea_dos_cifras(self):
        notas = [Decimal("10"), Decimal("10"), Decimal("11")]
        resultado = SubNotaValidationService.calcular_nota_final_sub_notas(notas)
        assert resultado == Decimal("10.33")

    def test_promedio_cinco_sub_notas(self):
        notas = [
            Decimal("20"),
            Decimal("18"),
            Decimal("16"),
            Decimal("14"),
            Decimal("12"),
        ]
        resultado = SubNotaValidationService.calcular_nota_final_sub_notas(notas)
        assert resultado == Decimal("16.00")

    def test_promedio_lista_vacia_retorna_cero(self):
        resultado = SubNotaValidationService.calcular_nota_final_sub_notas([])
        assert resultado == Decimal("0.00")

    def test_promedio_acepta_strings_numericos(self):
        """El servicio normaliza valores con Decimal(str(...)) como el resto del dominio."""
        resultado = SubNotaValidationService.calcular_nota_final_sub_notas(
            ["15.50", "16.50", "17.00"]
        )
        assert resultado == Decimal("16.33")

    def test_override_igual_al_promedio_no_requiere_justificacion(self):
        assert (
            SubNotaValidationService.requiere_justificacion_override(
                Decimal("15.00"), Decimal("15.00")
            )
            is False
        )

    def test_override_distinto_al_promedio_requiere_justificacion(self):
        assert (
            SubNotaValidationService.requiere_justificacion_override(
                Decimal("15.00"), Decimal("16.00")
            )
            is True
        )

    def test_override_diferencia_minima_requiere_justificacion(self):
        assert (
            SubNotaValidationService.requiere_justificacion_override(
                Decimal("15.00"), Decimal("15.01")
            )
            is True
        )

    def test_pesos_que_suman_cien_son_validos(self):
        pesos = [Decimal("20"), Decimal("30"), Decimal("50")]
        assert SubNotaValidationService.validar_pesos_sub_notas(pesos) is True

    def test_pesos_que_no_suman_cien_son_invalidos(self):
        pesos = [Decimal("20"), Decimal("30"), Decimal("40")]
        assert SubNotaValidationService.validar_pesos_sub_notas(pesos) is False

    def test_pesos_con_cero_o_negativos_son_invalidos(self):
        assert (
            SubNotaValidationService.validar_pesos_sub_notas(
                [Decimal("0"), Decimal("50"), Decimal("50")]
            )
            is False
        )
        assert (
            SubNotaValidationService.validar_pesos_sub_notas(
                [Decimal("-10"), Decimal("60"), Decimal("50")]
            )
            is False
        )

    def test_pesos_lista_vacia_invalida(self):
        assert SubNotaValidationService.validar_pesos_sub_notas([]) is False

    def test_pesos_con_decimales_validos(self):
        pesos = [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        assert SubNotaValidationService.validar_pesos_sub_notas(pesos) is True

    def test_nota_final_ponderada(self):
        notas = [Decimal("15"), Decimal("18"), Decimal("12")]
        pesos = [Decimal("20"), Decimal("30"), Decimal("50")]
        resultado = SubNotaValidationService.calcular_nota_final_ponderada(notas, pesos)
        # 15*0.20 + 18*0.30 + 12*0.50 = 3 + 5.4 + 6 = 14.40
        assert resultado == Decimal("14.40")

    def test_nota_final_ponderada_redondea_dos_cifras(self):
        notas = [Decimal("10"), Decimal("10"), Decimal("11")]
        pesos = [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        resultado = SubNotaValidationService.calcular_nota_final_ponderada(notas, pesos)
        assert resultado == Decimal("10.33")

    def test_nota_final_ponderada_lista_vacia_retorna_cero(self):
        resultado = SubNotaValidationService.calcular_nota_final_ponderada([], [])
        assert resultado == Decimal("0.00")

    def test_nota_final_ponderada_acepta_strings(self):
        resultado = SubNotaValidationService.calcular_nota_final_ponderada(
            ["20", "10"], ["50", "50"]
        )
        assert resultado == Decimal("15.00")
