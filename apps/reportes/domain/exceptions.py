"""
Domain exceptions for the Reportes bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class PeriodoSinEstudiantesError(Exception):
    """Raised when trying to generate a report for a period with no active students."""


class ReporteGeneracionError(Exception):
    """Raised when PDF generation fails."""
