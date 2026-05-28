"""
Domain services for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.

Services encapsulate domain rules that don't belong to a single entity.
"""

from datetime import date
from typing import Optional

from .exceptions import (
    AsignaturaCodigoDuplicadoError,
    CapacidadParaleloInvalidaError,
    CupoExcedidoError,
    DocenteInvalidoError,
    DuracionPeriodoInvalidaError,
    EstadoMatriculaInvalidoError,
    HorasLectivasInvalidasError,
    MatriculaAsignaturaDuplicadaError,
    MatriculaDuplicadaError,
    ParaleloDuplicadoError,
    PeriodoActivoExistenteError,
    PeriodoInactivoError,
    PeriodoSolapadoError,
)


class PeriodoService:
    """
    Domain rules for academic periods.
    Enforces one-active-per-tipo-licencia invariant and date validation.
    """

    def validar_fechas(self, fecha_inicio: date, fecha_fin: date) -> None:
        """Validate that fecha_inicio < fecha_fin."""
        if fecha_inicio >= fecha_fin:
            raise PeriodoSolapadoError("La fecha de inicio debe ser anterior a la fecha de fin.")

    def validar_duracion(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        minimo: int,
        maximo: int,
    ) -> None:
        """Validate periodo duration in [minimo, maximo] months (lenient: any trailing days bump up)."""
        from dateutil.relativedelta import relativedelta

        delta = relativedelta(fecha_fin, fecha_inicio)
        meses = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
        if meses < minimo or meses > maximo:
            raise DuracionPeriodoInvalidaError(meses=meses, minimo=minimo, maximo=maximo)

    def verificar_activacion(
        self,
        periodo_activo_actual: Optional[str],
        confirmar_desactivacion: bool,
    ) -> bool:
        """
        Check if activation can proceed for a given tipo_licencia.

        Args:
            periodo_activo_actual: Name of the currently active period
                for this tipo_licencia, or None.
            confirmar_desactivacion: Whether the user confirmed deactivation.

        Returns:
            True if activation can proceed.

        Raises:
            PeriodoActivoExistenteError: If there's an active period for
                this tipo_licencia and user hasn't confirmed deactivation.
        """
        if periodo_activo_actual is None:
            return True

        if confirmar_desactivacion:
            return True

        raise PeriodoActivoExistenteError(
            f"El período '{periodo_activo_actual}' ya está activo para este tipo de licencia. "
            "¿Desea desactivarlo para activar el nuevo período?"
        )


class AsignaturaService:
    """
    Domain rules for subjects.
    Validates codigo uniqueness, horas_lectivas per licencia > 0, at least one tipo_licencia.
    """

    def validar_horas_lectivas(self, horas: int, maximo: int = 60) -> None:
        """
        Validate that horas_lectivas is within [1, maximo].
        
        Args:
            horas: Number of teaching hours.
            maximo: Maximum allowed hours (default: 60 per settings).
        
        Raises:
            HorasLectivasInvalidasError: If horas < 1 or horas > maximo.
        """
        if horas < 1 or horas > maximo:
            raise HorasLectivasInvalidasError(horas=horas, maximo=maximo)

    def validar_datos(
        self,
        codigo: str,
        licencias: list,
        codigo_exists: bool,
    ) -> None:
        """
        Validate subject data at the domain level.

        Args:
            licencias: List of dicts with tipo_licencia_id and horas_lectivas.

        Raises:
            AsignaturaCodigoDuplicadoError: If codigo already exists.
            ValueError: If no licencias or any horas_lectivas <= 0.
        """
        if codigo_exists:
            raise AsignaturaCodigoDuplicadoError(
                f"Ya existe una asignatura con el código '{codigo}'."
            )

        if not licencias:
            raise ValueError("La asignatura debe estar asociada a al menos un tipo de licencia.")

        for entry in licencias:
            horas = entry.get("horas_lectivas", 0)
            if horas <= 0:
                raise ValueError("Las horas lectivas deben ser mayores a 0.")


class ParaleloService:
    """
    Domain rules for parallels.
    Validates docente role, active period, and unique combination.
    """

    def validar_docente(self, docente_rol: str) -> None:
        """Validate that the assigned user has the docente role."""
        if docente_rol != "docente":
            raise DocenteInvalidoError("El usuario asignado debe tener el rol 'docente'.")

    def validar_capacidad(self, capacidad: int, maximo: int) -> None:
        """
        Validate that capacidad is within [1, maximo].

        Args:
            capacidad: Maximum students for the paralelo.
            maximo: Upper bound allowed (injected from settings).

        Raises:
            CapacidadParaleloInvalidaError: If capacidad < 1 or capacidad > maximo.
        """
        if capacidad < 1 or capacidad > maximo:
            raise CapacidadParaleloInvalidaError(capacidad=capacidad, maximo=maximo)

    def validar_periodo_activo(self, periodo_activo: bool) -> None:
        """Validate that the associated period is active."""
        if not periodo_activo:
            raise PeriodoInactivoError("Solo se pueden crear paralelos en un período activo.")

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
            raise MatriculaDuplicadaError("El estudiante ya tiene una matrícula en este paralelo.")

    def validar_asignatura_no_duplicada(
        self,
        ya_inscrito: bool,
        asignatura_nombre: str = "",
        paralelo_existente: str = "",
    ) -> None:
        """Validate that the student is not already enrolled in the same asignatura."""
        if ya_inscrito:
            msg = "El estudiante ya se encuentra inscrito en esta asignatura"
            if asignatura_nombre and paralelo_existente:
                msg = (
                    f"El estudiante ya se encuentra inscrito en la asignatura "
                    f"{asignatura_nombre} en el paralelo {paralelo_existente}."
                )
            else:
                msg += "."
            raise MatriculaAsignaturaDuplicadaError(msg)

    def validar_periodo_activo(self, periodo_activo: bool) -> None:
        """Validate that the paralelo belongs to an active period."""
        if not periodo_activo:
            raise PeriodoInactivoError(
                "Solo se pueden registrar matrículas en paralelos " "de un período activo."
            )

    def validar_transicion_estado(self, estado_actual: str, nuevo_estado: str, rol: str) -> None:
        """Validate that the state transition is allowed for the given role."""
        if estado_actual == nuevo_estado:
            return

        if rol == "secretaria":
            transiciones = self.TRANSICIONES_SECRETARIA
        elif rol == "inspector":
            transiciones = self.TRANSICIONES_INSPECTOR
        else:
            raise EstadoMatriculaInvalidoError(
                f"El rol '{rol}' no tiene permisos para cambiar " f"el estado de matrículas."
            )

        estados_permitidos = transiciones.get(estado_actual, [])
        if nuevo_estado not in estados_permitidos:
            raise EstadoMatriculaInvalidoError(
                f"No se puede cambiar el estado de '{estado_actual}' "
                f"a '{nuevo_estado}' con el rol '{rol}'."
            )
