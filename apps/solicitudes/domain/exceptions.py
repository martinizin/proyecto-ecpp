"""
Domain-specific exceptions for the Solicitudes bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class SolicitudError(Exception):
    """Base exception for Solicitud domain errors."""


class SolicitudYaResueltaError(SolicitudError):
    """Raised when trying to resolve an already-resolved request."""
