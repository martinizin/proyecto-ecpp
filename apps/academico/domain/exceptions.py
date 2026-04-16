"""
Domain-specific exceptions for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class AcademicoError(Exception):
    """Base exception for Academico domain errors."""


class PeriodoSolapadoError(AcademicoError):
    """Raised when a new period overlaps with an existing one."""


class PeriodoActivoExistenteError(AcademicoError):
    """Raised when trying to activate a period while another is already active."""


class PeriodoInactivoError(AcademicoError):
    """Raised when an operation requires an active period but none is found."""


class AsignaturaCodigoDuplicadoError(AcademicoError):
    """Raised when a duplicate subject code is detected."""


class DocenteInvalidoError(AcademicoError):
    """Raised when a user assigned as docente does not have the docente role."""


class ParaleloDuplicadoError(AcademicoError):
    """Raised when a duplicate paralelo is detected."""


class CupoExcedidoError(AcademicoError):
    """Raised when a paralelo has reached its maximum capacity."""


class MatriculaDuplicadaError(AcademicoError):
    """Raised when a student is already enrolled in a paralelo."""


class EstadoMatriculaInvalidoError(AcademicoError):
    """Raised when an invalid state transition is attempted on a matricula."""
