"""
Domain services for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.

Services encapsulate domain rules that don't belong to a single entity.
"""

from datetime import date
from typing import Optional

from .exceptions import (
    AsignaturaCodigoDuplicadoError,
    CupoExcedidoError,
    DocenteInvalidoError,
    EstadoMatriculaInvalidoError,
    MatriculaDuplicadaError,
    ParaleloDuplicadoError,
    PeriodoActivoExistenteError,
    PeriodoInactivoError,
    PeriodoSolapadoError,
)


class PeriodoService:
    """
    Domain rules for academic periods.
    Enforces single-active invariant and date validation.
    """

    def validar_fechas(self, fecha_inicio: date, fecha_fin: date) -> None:
        """Validate that fecha_inicio < fecha_fin."""
        if fecha_inicio >= fecha_fin:
            raise PeriodoSolapadoError(
                "La fecha de inicio debe ser anterior a la fecha de fin."
            )

    def verificar_activacion(
        self,
        periodo_activo_actual: Optional[str],
        confirmar_desactivacion: bool,
    ) -> bool:
        """
        Check if activation can proceed.

        Args:
            periodo_activo_actual: Name of the currently active period, or None.
            confirmar_desactivacion: Whether the user confirmed deactivation.

        Returns:
            True if activation can proceed.

        Raises:
            PeriodoActivoExistenteError: If there's an active period and
                user hasn't confirmed deactivation.
        """
        if periodo_activo_actual is None:
            # No active period — activate directly (SCN-PER-08)
            return True

        if confirmar_desactivacion:
            # User confirmed — proceed (SCN-PER-06)
            return True

        # Active period exists but no confirmation (SCN-PER-05)
        raise PeriodoActivoExistenteError(
            f"El período '{periodo_activo_actual}' está activo. "
            "¿Desea desactivarlo para activar el nuevo período?"
        )


class AsignaturaService:
    """
    Domain rules for subjects.
    Validates codigo uniqueness, horas_lectivas > 0, at least one tipo_licencia.
    """

    def validar_datos(
        self,
        codigo: str,
        horas_lectivas: int,
        tipos_licencia_ids: list,
        codigo_exists: bool,
    ) -> None:
        """
        Validate subject data at the domain level.

        Raises:
            AsignaturaCodigoDuplicadoError: If codigo already exists.
            ValueError: If horas_lectivas <= 0 or no tipos_licencia.
        """
        if codigo_exists:
            raise AsignaturaCodigoDuplicadoError(
                f"Ya existe una asignatura con el código '{codigo}'."
            )

        if horas_lectivas <= 0:
            raise ValueError(
                "Las horas lectivas deben ser mayores a 0."
            )

        if not tipos_licencia_ids:
            raise ValueError(
                "La asignatura debe estar asociada a al menos un tipo de licencia."
            )


class ParaleloService:
    """
    Domain rules for parallels.
    Validates docente role, active period, and unique combination.
    """

    def validar_docente(self, docente_rol: str) -> None:
        """Validate that the assigned user has the docente role."""
        if docente_rol != "docente":
            raise DocenteInvalidoError(
                "El usuario asignado debe tener el rol 'docente'."
            )

    def validar_periodo_activo(self, periodo_activo: bool) -> None:
        """Validate that the associated period is active."""
        if not periodo_activo:
            raise PeriodoInactivoError(
                "Solo se pueden crear paralelos en un período activo."
            )

    def validar_unicidad(
        self,
        combinacion_exists: bool,
    ) -> None:
        """
        Validate uniqueness of (periodo, tipo_licencia, asignatura, nombre).
        """
        if combinacion_exists:
            raise ParaleloDuplicadoError(
                "Ya existe un paralelo con la misma combinación de "
                "período, tipo de licencia, asignatura y nombre."
            )

    def validar_datos(
        self,
        docente_rol: str,
        periodo_activo: bool,
        combinacion_exists: bool,
    ) -> None:
        """Convenience method to run all parallel validations."""
        self.validar_docente(docente_rol)
        self.validar_periodo_activo(periodo_activo)
        self.validar_unicidad(combinacion_exists)


class MatriculaService:
    """
    Domain rules for student enrollments.
    Validates capacity, active period, no duplicates, and state transitions.
    """

    # Valid state transitions per role
    TRANSICIONES_SECRETARIA = {
        "activa": ["retirada"],
        "retirada": ["activa"],
        "suspendida": [],  # Secretaría no puede cambiar suspendida
    }
    TRANSICIONES_INSPECTOR = {
        "activa": ["suspendida"],
        "suspendida": ["activa"],
        "retirada": [],  # Inspector no puede cambiar retirada
    }

    def validar_cupo(self, activas_en_paralelo: int, capacidad_maxima: int) -> None:
        """Validate that the paralelo has not reached its capacity."""
        if activas_en_paralelo >= capacidad_maxima:
            raise CupoExcedidoError(
                f"El paralelo ha alcanzado su capacidad máxima "
                f"de {capacidad_maxima} estudiantes."
            )

    def validar_no_duplicada(self, matricula_existente: bool) -> None:
        """Validate that the student is not already enrolled in the paralelo."""
        if matricula_existente:
            raise MatriculaDuplicadaError(
                "El estudiante ya tiene una matrícula en este paralelo."
            )

    def validar_periodo_activo(self, periodo_activo: bool) -> None:
        """Validate that the paralelo belongs to an active period."""
        if not periodo_activo:
            raise PeriodoInactivoError(
                "Solo se pueden registrar matrículas en paralelos "
                "de un período activo."
            )

    def validar_transicion_estado(
        self, estado_actual: str, nuevo_estado: str, rol: str
    ) -> None:
        """Validate that the state transition is allowed for the given role."""
        if estado_actual == nuevo_estado:
            return

        if rol == "secretaria":
            transiciones = self.TRANSICIONES_SECRETARIA
        elif rol == "inspector":
            transiciones = self.TRANSICIONES_INSPECTOR
        else:
            raise EstadoMatriculaInvalidoError(
                f"El rol '{rol}' no tiene permisos para cambiar "
                f"el estado de matrículas."
            )

        estados_permitidos = transiciones.get(estado_actual, [])
        if nuevo_estado not in estados_permitidos:
            raise EstadoMatriculaInvalidoError(
                f"No se puede cambiar el estado de '{estado_actual}' "
                f"a '{nuevo_estado}' con el rol '{rol}'."
            )
