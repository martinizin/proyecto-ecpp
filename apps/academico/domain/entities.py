"""
Domain entities for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure. Full domain logic comes in Sprint 1+.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class PeriodoEntity:
    """Domain representation of an academic period."""

    nombre: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool = False


@dataclass(frozen=True)
class AsignaturaEntity:
    """Domain representation of a course/subject."""

    nombre: str
    codigo: str
    descripcion: str = ""


@dataclass(frozen=True)
class ParaleloEntity:
    """Domain representation of a class section."""

    asignatura_codigo: str
    periodo_nombre: str
    docente_username: str
    nombre: str
    horario: str = ""
