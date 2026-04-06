"""
Domain entities for the Solicitudes bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TipoSolicitud(str, Enum):
    """Types of requests students can submit."""

    RECTIFICACION = "rectificacion"
    JUSTIFICACION = "justificacion"


class EstadoSolicitud(str, Enum):
    """Status of a student request."""

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass(frozen=True)
class SolicitudEntity:
    """Domain representation of a student request."""

    tipo: TipoSolicitud
    estudiante_id: int
    descripcion: str
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
    fecha_creacion: Optional[datetime] = None
    fecha_resolucion: Optional[datetime] = None
    resuelto_por_id: Optional[int] = None
    respuesta: str = ""
