"""
Domain-specific exceptions for the Asistencia bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class AsistenciaError(Exception):
    """Base exception for Asistencia domain errors."""


class AsistenciaDuplicadaError(AsistenciaError):
    """Raised when a duplicate attendance record is detected."""
