"""
Value objects for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure. Full value objects come in Sprint 1+.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Cedula:
    """Ecuadorian identification number (cedula)."""

    valor: str

    def __post_init__(self) -> None:
        if self.valor and len(self.valor) > 13:
            raise ValueError("La cedula no puede tener mas de 13 caracteres.")
