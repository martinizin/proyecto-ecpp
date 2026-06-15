"""
Domain services for the Academico bounded context.
Pure Python in spirit — `HorarioConflictoService` is the single intentional
exception (queries Django ORM directly per design §3 to keep the budget under
2 round-trips). All other services in this module stay framework-agnostic.

Services encapsulate domain rules that don't belong to a single entity.
"""

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple

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
    MaxAsignaturasExcedidasError,
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
        """Validate periodo duration in [minimo, maximo] months.

        Lenient: any trailing days bump the month count up.
        """
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

    def validar_horas_lectivas(self, horas: int, maximo: int = 60, minimo: int = 1) -> None:
        """
        Validate that horas_lectivas is within [minimo, maximo].

        Args:
            horas: Number of teaching hours.
            maximo: Maximum allowed hours (default: 60 per settings).
            minimo: Minimum allowed hours (default: 1; presentation layer
                typically passes settings.HORAS_LECTIVAS_MIN).

        Raises:
            HorasLectivasInvalidasError: If horas < minimo or horas > maximo.
        """
        if horas < minimo or horas > maximo:
            raise HorasLectivasInvalidasError(horas=horas, maximo=maximo, minimo=minimo)

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

    def validar_max_asignaturas_por_periodo(
        self,
        asignaturas_existentes_ids: Iterable[int],
        asignaturas_nuevas_ids: Iterable[int],
        limite: int,
        tipo_licencia_codigo: str,
    ) -> None:
        """
        Validate that the union of existing + new asignaturas for a (periodo, tipo_licencia)
        does not exceed ``limite`` (tipo_licencia.num_asignaturas).

        Pure function — no DB access. Adapters are responsible for building the
        ``asignaturas_existentes_ids`` queryset, excluding ``self.instance.pk`` when
        editing so the same asignatura is not double-counted.

        Args:
            asignaturas_existentes_ids: IDs of asignaturas already linked to the
                (periodo, tipo_licencia) tuple (queryset / list of ints).
            asignaturas_nuevas_ids: IDs of asignaturas about to be created (list of ints).
            limite: Maximum unique asignaturas allowed (tipo_licencia.num_asignaturas).
            tipo_licencia_codigo: Code (e.g. 'C', 'E', 'EC') for the error message.

        Raises:
            MaxAsignaturasExcedidasError: If union size > limite.
        """
        union = set(asignaturas_existentes_ids) | set(asignaturas_nuevas_ids)
        actual = len(union)
        if actual > limite:
            raise MaxAsignaturasExcedidasError(
                actual=actual,
                limite=limite,
                tipo_licencia_codigo=tipo_licencia_codigo,
            )


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


# ---------------------------------------------------------------------------
# HU21 V5 — Conflictos de horario (design §2.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Conflicto:
    """
    DTO inmutable que representa un conflicto de horario detectado.

    Producido por `HorarioConflictoService` y consumido por la capa de
    presentación (template `conflicto_horario_error.html`) y por
    `exception_mapping.to_drf` (serializado a JSON vía `asdict()` +
    `isoformat()` sobre los `time`).

    Campos alineados 1:1 con design §2.1 (orden posicional estable).
    """

    paralelo_id: int
    paralelo_nombre: str
    asignatura_codigo: str
    asignatura_nombre: str
    dia_semana: str
    dia_semana_label: str
    hora_inicio: time
    hora_fin: time


def _overlap(
    b_dia: str,
    b_inicio: time,
    b_fin: time,
    p_dia: str,
    p_inicio: time,
    p_fin: time,
) -> bool:
    """Half-open overlap check (design §2.3).

    Two time ranges on the same day overlap iff one starts before the other
    ends. Back-to-back blocks (b_fin == p_inicio) are NOT a conflict.
    """
    return b_dia == p_dia and b_inicio < p_fin and p_inicio < b_fin


class HorarioConflictoService:
    """
    Detecta conflictos de horario para docentes y estudiantes (design §2 + §3).

    Algoritmo half-open (`hi1 < hf2 AND hi2 < hf1`): bloques back-to-back
    (e.g. 08-10 vs 10-12) NO son conflicto. Ver design §2.3.

    Excepción a la regla "domain sin Django": estos métodos consultan el ORM
    directamente para mantener el budget en ≤ 2 queries (design §3.3) sin
    forzar al adaptador a duplicar el armado del queryset.
    """

    @staticmethod
    def detectar_conflicto_docente(
        docente_id: int,
        periodo_id: int,
        bloques_propuestos: list[tuple[str, time, time]],
        paralelo_id_excluir: int | None = None,
    ) -> list["Conflicto"]:
        """
        Detecta solapes para todos los bloques que el docente ya dicta en el
        mismo período, opcionalmente excluyendo un paralelo (modo edición).

        Queryset per design §3.1: filter por `paralelo__docente_id` +
        `paralelo__periodo_id`, `select_related("paralelo__asignatura")`,
        `.exclude(paralelo_id=...)` para excluir self.
        """
        if not bloques_propuestos:
            return []

        from apps.academico.infrastructure.models import BloqueHorario

        qs = BloqueHorario.objects.filter(
            paralelo__docente_id=docente_id,
            paralelo__periodo_id=periodo_id,
        ).select_related("paralelo__asignatura")
        if paralelo_id_excluir is not None:
            qs = qs.exclude(paralelo_id=paralelo_id_excluir)

        conflictos: list[Conflicto] = []
        for bloque in qs:
            for dia, hi, hf in bloques_propuestos:
                if _overlap(
                    bloque.dia_semana,
                    bloque.hora_inicio,
                    bloque.hora_fin,
                    dia,
                    hi,
                    hf,
                ):
                    conflictos.append(
                        Conflicto(
                            paralelo_id=bloque.paralelo_id,
                            paralelo_nombre=bloque.paralelo.nombre,
                            asignatura_codigo=bloque.paralelo.asignatura.codigo,
                            asignatura_nombre=bloque.paralelo.asignatura.nombre,
                            dia_semana=bloque.dia_semana,
                            dia_semana_label=bloque.get_dia_semana_display(),
                            hora_inicio=bloque.hora_inicio,
                            hora_fin=bloque.hora_fin,
                        )
                    )
        return conflictos

    @staticmethod
    def detectar_conflicto_estudiante(
        estudiante_id: int,
        periodo_id: int,
        bloques_propuestos: list[tuple[str, time, time]],
        matricula_id_excluir: int | None = None,
    ) -> list["Conflicto"]:
        """
        Detecta solapes para todos los bloques de paralelos donde el
        estudiante tenga matrícula ACTIVA en el mismo período, opcionalmente
        excluyendo una matrícula puntual (modo edición).

        Queryset per design §3.2: filter por
        `paralelo__matriculas__estudiante_id` con `estado=ACTIVA` y
        `paralelo__periodo_id`, `select_related("paralelo__asignatura")`,
        `.distinct()` para evitar duplicar bloques por la unión con
        Matricula. Matrículas RETIRADA / SUSPENDIDA quedan filtradas
        (design §7 R2.2 + R5.1).
        """
        if not bloques_propuestos:
            return []

        from apps.academico.infrastructure.models import BloqueHorario, Matricula

        qs = (
            BloqueHorario.objects.filter(
                paralelo__matriculas__estudiante_id=estudiante_id,
                paralelo__matriculas__estado=Matricula.Estado.ACTIVA,
                paralelo__periodo_id=periodo_id,
            )
            .select_related("paralelo__asignatura")
            .distinct()
        )
        if matricula_id_excluir is not None:
            qs = qs.exclude(paralelo__matriculas__id=matricula_id_excluir)

        conflictos: list[Conflicto] = []
        for bloque in qs:
            for dia, hi, hf in bloques_propuestos:
                if _overlap(
                    bloque.dia_semana,
                    bloque.hora_inicio,
                    bloque.hora_fin,
                    dia,
                    hi,
                    hf,
                ):
                    conflictos.append(
                        Conflicto(
                            paralelo_id=bloque.paralelo_id,
                            paralelo_nombre=bloque.paralelo.nombre,
                            asignatura_codigo=bloque.paralelo.asignatura.codigo,
                            asignatura_nombre=bloque.paralelo.asignatura.nombre,
                            dia_semana=bloque.dia_semana,
                            dia_semana_label=bloque.get_dia_semana_display(),
                            hora_inicio=bloque.hora_inicio,
                            hora_fin=bloque.hora_fin,
                        )
                    )
        return conflictos


class RendimientoAcademicoService:
    """
    Pure domain service for academic performance calculations.
    No ORM dependency — receives plain Python values.
    """

    NOTA_APROBACION = Decimal("16")

    @staticmethod
    def calcular_promedio_paralelo(notas: List[Decimal]) -> Decimal:
        """Average of all student grades in a paralelo. Returns 0 if empty."""
        if not notas:
            return Decimal("0.00")
        return (sum(notas) / Decimal(len(notas))).quantize(Decimal("0.01"))

    @staticmethod
    def calcular_tasa_aprobacion(aprobados: int, total: int) -> Decimal:
        """Percentage of students with final grade >= 16."""
        if total == 0:
            return Decimal("0.0")
        return (Decimal(aprobados) / Decimal(total) * 100).quantize(Decimal("0.1"))

    @staticmethod
    def calcular_porcentaje_asistencia(presentes: int, total_registros: int) -> Decimal:
        """Overall attendance percentage for a paralelo."""
        if total_registros == 0:
            return Decimal("0.0")
        return (Decimal(presentes) / Decimal(total_registros) * 100).quantize(Decimal("0.1"))

    @classmethod
    def clasificar_estudiante(cls, promedio: Decimal) -> str:
        """Returns aprobado or reprobado based on grade."""
        if promedio >= cls.NOTA_APROBACION:
            return "aprobado"
        return "reprobado"

    @classmethod
    def calcular_promedios_por_estudiante(
        cls,
        notas_por_estudiante: List[Tuple[int, List[Tuple[Decimal, Decimal]]]],
    ) -> List[Tuple[int, Decimal]]:
        """
        Calculates weighted average per student.

        Args:
            notas_por_estudiante: List of (estudiante_id, [(nota, peso), ...])

        Returns:
            List of (estudiante_id, promedio_ponderado)
        """
        resultados = []
        for estudiante_id, notas_pesos in notas_por_estudiante:
            if not notas_pesos:
                resultados.append((estudiante_id, Decimal("0.00")))
                continue
            total = sum(nota * peso / 100 for nota, peso in notas_pesos)
            resultados.append((estudiante_id, total.quantize(Decimal("0.01"))))
        return resultados
