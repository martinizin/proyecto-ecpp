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


class MatriculaAsignaturaDuplicadaError(AcademicoError):
    """Raised when a student is already enrolled in the same asignatura (any paralelo)."""


class EstadoMatriculaInvalidoError(AcademicoError):
    """Raised when an invalid state transition is attempted on a matricula."""


# ============================================================
# Excepciones de validación de negocio — HU21 QA V1-V4
# ============================================================
# Estas excepciones llevan contexto numérico (valor recibido + límite)
# para que los adaptadores puedan armar mensajes precisos y los tests
# puedan asertar sobre los valores sin parsear strings.


class HorasLectivasInvalidasError(AcademicoError):
    """V2 — Las horas lectivas exceden el tope permitido o no son positivas."""

    def __init__(self, horas: int, maximo: int):
        self.horas = horas
        self.maximo = maximo
        super().__init__(
            f"Las horas lectivas deben estar entre 1 y {maximo} (recibido: {horas})."
        )


class CapacidadParaleloInvalidaError(AcademicoError):
    """V3 — La capacidad del paralelo está fuera del rango permitido."""

    def __init__(self, capacidad: int, maximo: int):
        self.capacidad = capacidad
        self.maximo = maximo
        super().__init__(
            f"La capacidad del paralelo debe estar entre 1 y {maximo} (recibido: {capacidad})."
        )


class DuracionPeriodoInvalidaError(AcademicoError):
    """V4 — La duración del periodo está fuera del rango permitido."""

    def __init__(self, meses: int, minimo: int, maximo: int):
        self.meses = meses
        self.minimo = minimo
        self.maximo = maximo
        super().__init__(
            f"La duración del periodo debe estar entre {minimo} y {maximo} meses (recibido: {meses})."
        )


class MaxAsignaturasExcedidasError(AcademicoError):
    """V1 — Se excede el máximo de asignaturas únicas por periodo según licencia."""

    def __init__(self, actual: int, limite: int, tipo_licencia_codigo: str):
        self.actual = actual
        self.limite = limite
        self.tipo_licencia_codigo = tipo_licencia_codigo
        super().__init__(
            f"La licencia {tipo_licencia_codigo} permite máximo {limite} asignaturas "
            f"por periodo (se intenta llegar a {actual})."
        )
