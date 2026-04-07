"""
Domain entities for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass(frozen=True)
class PeriodoEntity:
    """Domain representation of an academic period."""

    nombre: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool = False
    creado_por_id: Optional[int] = None


@dataclass(frozen=True)
class TipoLicenciaEntity:
    """Domain representation of a license type (C, E, EC)."""

    nombre: str
    codigo: str
    duracion_meses: int
    num_asignaturas: int
    activo: bool = True


@dataclass(frozen=True)
class AsignaturaEntity:
    """Domain representation of a course/subject."""

    nombre: str
    codigo: str
    descripcion: str = ""
    horas_lectivas: int = 40
    tipos_licencia_ids: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class ParaleloEntity:
    """Domain representation of a class section."""

    asignatura_codigo: str
    periodo_nombre: str
    docente_username: str
    nombre: str
    horario: str = ""
    tipo_licencia_id: Optional[int] = None
    capacidad_maxima: int = 30
