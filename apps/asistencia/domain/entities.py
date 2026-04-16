"""
Domain entities for the Asistencia bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class EstadoAsistencia(str, Enum):
    """Attendance states."""

    PRESENTE = "presente"
    AUSENTE = "ausente"
    JUSTIFICADO = "justificado"


@dataclass(frozen=True)
class AsistenciaEntity:
    """Domain representation of an attendance record."""

    estudiante_id: int
    paralelo_id: int
    fecha: date
    estado: EstadoAsistencia = EstadoAsistencia.AUSENTE
    observaciones: str = ""
