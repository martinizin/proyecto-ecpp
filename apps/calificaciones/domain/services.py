"""
Domain services for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from decimal import Decimal

from apps.calificaciones.domain.exceptions import (
    PesosInvalidosError,
    SubNotasFueraDeRangoError,
)
from apps.calificaciones.domain.value_objects import NOTA_APROBACION, Nota

TOLERANCIA_PESOS = Decimal("0.01")


class CalificacionValidationService:
    """Domain service: validates grades and evaluation weight distributions."""

    @staticmethod
    def validar_nota(valor) -> Nota:
        """
        Construye y retorna un VO Nota validado.

        Args:
            valor: Valor numérico de la nota (str, int o Decimal).

        Returns:
            Nota: value object inmutable con el valor normalizado.

        Raises:
            NotaFueraDeRangoError: si el valor está fuera del rango 0.00–20.00.
        """
        return Nota(valor=Decimal(str(valor)))

    @staticmethod
    def validar_pesos_evaluaciones(pesos: dict[str, Decimal]) -> None:
        """Raise PesosInvalidosError if the weights do not sum to 100."""
        total = sum(Decimal(str(p)) for p in pesos.values())
        if abs(total - Decimal("100.00")) > TOLERANCIA_PESOS:
            raise PesosInvalidosError(
                f"Los pesos de las evaluaciones suman {total}, deben sumar 100."
            )

    @staticmethod
    def calcular_promedio_ponderado(notas_con_pesos: list[tuple[Decimal, Decimal]]) -> Decimal:
        """
        Calculate weighted average.
        notas_con_pesos: [(nota_valor, peso_porcentual), ...]
        """
        if not notas_con_pesos:
            return Decimal("0.00")
        total_peso = sum(Decimal(str(peso)) for _, peso in notas_con_pesos)
        if total_peso == 0:
            return Decimal("0.00")
        promedio = (
            sum(Decimal(str(nota)) * Decimal(str(peso)) for nota, peso in notas_con_pesos)
            / total_peso
        )
        return promedio.quantize(Decimal("0.01"))

    @staticmethod
    def estado_aprobacion(promedio: Decimal) -> str:
        """Return 'aprobado' or 'reprobado' based on the weighted average."""
        if Decimal(str(promedio)) >= NOTA_APROBACION:
            return "aprobado"
        return "reprobado"


class SubNotaValidationService:
    """Domain service: validates sub-grades within a parcial (HU32)."""

    MIN_SUB_NOTAS = 3
    MAX_SUB_NOTAS = 5

    @classmethod
    def validar_cantidad(cls, cantidad: int) -> None:
        """Raise SubNotasFueraDeRangoError if the count is outside 3–5."""
        if not (cls.MIN_SUB_NOTAS <= cantidad <= cls.MAX_SUB_NOTAS):
            raise SubNotasFueraDeRangoError(cantidad, cls.MIN_SUB_NOTAS, cls.MAX_SUB_NOTAS)

    @staticmethod
    def calcular_nota_final_sub_notas(notas: list[Decimal]) -> Decimal:
        """Arithmetic average of the sub-grades, rounded to 2 decimals."""
        if not notas:
            return Decimal("0.00")
        total = sum(Decimal(str(n)) for n in notas)
        return (total / len(notas)).quantize(Decimal("0.01"))

    @staticmethod
    def validar_pesos_sub_notas(pesos: list[Decimal]) -> bool:
        """Los pesos porcentuales de las sub-notas deben sumar exactamente 100."""
        if not pesos:
            return False
        if any(Decimal(str(p)) <= 0 for p in pesos):
            return False
        return sum(Decimal(str(p)) for p in pesos) == Decimal("100")

    @staticmethod
    def calcular_nota_final_ponderada(notas: list[Decimal], pesos: list[Decimal]) -> Decimal:
        """Weighted final grade: sum(nota * peso) / 100, rounded to 2 decimals."""
        if not notas:
            return Decimal("0.00")
        total = sum(Decimal(str(nota)) * Decimal(str(peso)) for nota, peso in zip(notas, pesos))
        return (total / Decimal("100")).quantize(Decimal("0.01"))

    @staticmethod
    def requiere_justificacion_override(promedio: Decimal, override: Decimal) -> bool:
        """The manual override requires justification if it differs from the average."""
        return Decimal(str(promedio)) != Decimal(str(override))
