"""
Value objects for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MetricasParalelo:
    """Aggregated academic performance metrics for a single paralelo."""

    paralelo_id: int
    paralelo_nombre: str
    asignatura_nombre: str
    asignatura_codigo: str
    docente_nombre: str
    promedio_general: Decimal
    porcentaje_asistencia: Decimal
    tasa_aprobacion: Decimal
    tasa_reprobacion: Decimal
    total_estudiantes: int
    estudiantes_aprobados: int
    estudiantes_reprobados: int
    estudiantes_en_curso: int


@dataclass
class TasasAsistencia:
    """Global attendance totals and rates for the period-closing dashboard (HU28)."""

    presentes: int
    ausentes: int
    justificados: int
    total: int
    tasa_presentes: Decimal
    tasa_ausentes: Decimal
    tasa_justificados: Decimal


@dataclass
class ResumenSolicitudes:
    """Totals by state and per-student average for one request type (HU28)."""

    total: int
    aprobadas: int
    rechazadas: int
    pendientes: int
    promedio_por_estudiante: Decimal
