"""
Domain entities for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class TipoEvaluacion(str, Enum):
    """Types of evaluations in the grading system."""

    PARCIAL_1 = "parcial1"
    PARCIAL_2_10H = "parcial2_10h"
    PARCIAL_3 = "parcial3"
    PARCIAL_4_10H = "parcial4_10h"
    PROYECTO = "proyecto"
    EXAMEN_FINAL = "examen_final"


@dataclass(frozen=True)
class EvaluacionEntity:
    """Domain representation of an evaluation."""

    paralelo_id: int
    tipo: TipoEvaluacion
    peso: Decimal
    fecha: Optional[date] = None
    descripcion: str = ""


@dataclass(frozen=True)
class CalificacionEntity:
    """Domain representation of a grade."""

    evaluacion_id: int
    estudiante_id: int
    nota: Decimal
    observaciones: str = ""
