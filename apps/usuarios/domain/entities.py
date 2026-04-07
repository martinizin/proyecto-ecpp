"""
Domain entities for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Rol(str, Enum):
    """Roles available in the system."""

    ESTUDIANTE = "estudiante"
    DOCENTE = "docente"
    INSPECTOR = "inspector"


@dataclass(frozen=True)
class UsuarioEntity:
    """
    Domain representation of a user.
    This is the pure domain entity — the ORM model lives in infrastructure.
    """

    username: str
    email: str
    rol: Rol
    first_name: str = ""
    last_name: str = ""
    cedula: Optional[str] = None
    telefono: str = ""
    direccion: str = ""
    is_active: bool = True


@dataclass(frozen=True)
class OTPTokenEntity:
    """Domain representation of a one-time password token."""

    usuario_id: int
    codigo: str
    creado_en: datetime
    expira_en: datetime
    usado: bool = False


@dataclass(frozen=True)
class RegistroAuditoriaEntity:
    """Domain representation of an audit log entry."""

    accion: str
    usuario_id: Optional[int] = None
    ip: Optional[str] = None
    timestamp: Optional[datetime] = None
    detalle: str = ""
