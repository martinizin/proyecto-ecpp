"""
Domain entities for the Reportes bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class DatosEstudianteReporte:
    """Snapshot of a student's academic data for the ANT report."""

    cedula: str
    nombres_completos: str
    paralelo_codigo: str
    materia_nombre: str
    porcentaje_asistencia: Decimal
    estado: str  # "aprobado" | "reprobado" | "en_curso" | "desertor"
    promedio_final: Optional[Decimal] = None
    calificaciones_por_evaluacion: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TotalesReporte:
    """Aggregated totals for the ANT report header."""

    total: int
    aprobados: int
    reprobados: int
    desertores: int
    en_curso: int
