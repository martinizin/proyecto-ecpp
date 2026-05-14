"""
Value objects for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from dataclasses import dataclass
from decimal import Decimal

from apps.calificaciones.domain.exceptions import NotaFueraDeRangoError, NotaDecimalError

NOTA_MINIMA = Decimal("0")
NOTA_MAXIMA = Decimal("20")
NOTA_APROBACION = Decimal("16")


@dataclass(frozen=True)
class Nota:
    """Value object representing a grade on the 0–20 integer scale."""

    valor: Decimal

    def __post_init__(self) -> None:
        valor = Decimal(str(self.valor))
        object.__setattr__(self, "valor", valor)
        if valor != valor.to_integral_value():
            raise NotaDecimalError(
                f"La nota {valor} debe ser un número entero (sin decimales)."
            )
        if valor < NOTA_MINIMA or valor > NOTA_MAXIMA:
            raise NotaFueraDeRangoError(
                f"La nota {valor} está fuera del rango permitido ({NOTA_MINIMA}–{NOTA_MAXIMA})."
            )

    @property
    def aprobado(self) -> bool:
        return self.valor >= NOTA_APROBACION

    def __str__(self) -> str:
        return str(int(self.valor))
