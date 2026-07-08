"""
Domain-specific exceptions for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class CalificacionesError(Exception):
    """Base exception for Calificaciones domain errors."""


class NotaFueraDeRangoError(CalificacionesError):
    """Raised when a grade value is outside the allowed 0–20 scale."""


class EvaluacionDuplicadaError(CalificacionesError):
    """Raised when a duplicate evaluation type is added to a paralelo."""


class PesosInvalidosError(CalificacionesError):
    """Raised when evaluation weights do not sum to 100."""


class SubNotasFueraDeRangoError(CalificacionesError):
    """Raised when the sub-grade count is outside the allowed 3–5 range."""

    def __init__(self, cantidad: int, minimo: int, maximo: int):
        self.cantidad = cantidad
        self.minimo = minimo
        self.maximo = maximo
        super().__init__(
            f"La cantidad de sub-notas ({cantidad}) debe estar " f"entre {minimo} y {maximo}."
        )
