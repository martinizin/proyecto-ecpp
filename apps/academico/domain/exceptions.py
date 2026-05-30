"""
Domain-specific exceptions for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Avoid runtime circular import: services.py already imports from exceptions.py.
    # Conflicto is only needed for type annotations here.
    from apps.academico.domain.services import Conflicto


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
    """V2 — Las horas lectivas están fuera del rango [minimo, maximo] permitido."""

    def __init__(self, horas: int, maximo: int, minimo: int = 1):
        self.horas = horas
        self.maximo = maximo
        self.minimo = minimo
        super().__init__(
            f"Las horas lectivas deben estar entre {minimo} y {maximo} (recibido: {horas})."
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
            f"La duración del periodo debe estar entre {minimo} y {maximo} meses "
            f"(recibido: {meses})."
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


# ============================================================
# Excepciones de conflicto de horario — HU21 QA V5
# ============================================================
# Estas excepciones llevan la lista de `Conflicto` detectados para que la
# capa de presentación pueda renderizar la tabla de conflictos (Tailwind
# partial) y para que `exception_mapping.to_drf` serialice el payload.


class ConflictoHorarioDocenteError(AcademicoError):
    """V5 — El docente ya tiene horario asignado que se solapa con el nuevo bloque."""

    def __init__(self, conflictos: "list[Conflicto]"):
        self.conflictos = conflictos
        count = len(conflictos)
        first = conflictos[0] if conflictos else None
        if first:
            msg = (
                f"El docente tiene {count} conflicto(s) de horario. "
                f"Primero: {first.paralelo_nombre} "
                f"({first.asignatura_codigo}) {first.dia_semana_label} "
                f"{first.hora_inicio:%H:%M}-{first.hora_fin:%H:%M}"
            )
        else:
            msg = "Conflicto de horario del docente"
        super().__init__(msg)


class ConflictoHorarioEstudianteError(AcademicoError):
    """V5 — El estudiante ya tiene matrícula activa con horario que se solapa."""

    def __init__(self, conflictos: "list[Conflicto]"):
        self.conflictos = conflictos
        count = len(conflictos)
        first = conflictos[0] if conflictos else None
        if first:
            msg = (
                f"El estudiante tiene {count} conflicto(s) de horario. "
                f"Primero: {first.paralelo_nombre} "
                f"({first.asignatura_codigo}) {first.dia_semana_label} "
                f"{first.hora_inicio:%H:%M}-{first.hora_fin:%H:%M}"
            )
        else:
            msg = "Conflicto de horario del estudiante"
        super().__init__(msg)
