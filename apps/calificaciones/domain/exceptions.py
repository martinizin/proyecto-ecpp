"""
Domain-specific exceptions for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class CalificacionesError(Exception):
    """Base exception for Calificaciones domain errors."""


class NotaInvalidaError(CalificacionesError):
    """Raised when a grade value is out of range."""


class NotaFueraDeRangoError(CalificacionesError):
    """Raised when a grade value is outside the allowed 0–20 scale."""


class NotaDecimalError(CalificacionesError):
    """Raised when a grade value has decimal places (only integers allowed)."""


class EvaluacionDuplicadaError(CalificacionesError):
    """Raised when a duplicate evaluation type is added to a paralelo."""


class PesosInvalidosError(CalificacionesError):
    """Raised when evaluation weights do not sum to 100."""
