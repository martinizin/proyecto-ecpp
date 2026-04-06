"""
Domain-specific exceptions for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class AcademicoError(Exception):
    """Base exception for Academico domain errors."""


class PeriodoSolapadoError(AcademicoError):
    """Raised when a new period overlaps with an existing one."""


class ParaleloDuplicadoError(AcademicoError):
    """Raised when a duplicate paralelo is detected."""
