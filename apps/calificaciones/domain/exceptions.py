"""
Domain-specific exceptions for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class CalificacionesError(Exception):
    """Base exception for Calificaciones domain errors."""


class NotaInvalidaError(CalificacionesError):
    """Raised when a grade value is out of range."""


class EvaluacionDuplicadaError(CalificacionesError):
    """Raised when a duplicate evaluation type is added to a paralelo."""
