"""
Domain entities for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure. Full domain logic comes in Sprint 1+.
"""

from dataclasses import dataclass
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
