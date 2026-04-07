"""
Repository interfaces for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.
Concrete implementations live in infrastructure/.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import OTPTokenEntity, RegistroAuditoriaEntity, UsuarioEntity


class UsuarioRepository(ABC):
    """Abstract repository for Usuario aggregate."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[UsuarioEntity]:
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UsuarioEntity]:
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[UsuarioEntity]:
        ...

    @abstractmethod
    def email_exists(self, email: str) -> bool:
        ...

    @abstractmethod
    def cedula_exists(self, cedula: str) -> bool:
        ...


class OTPTokenRepository(ABC):
    """Abstract repository for OTPToken management."""

    @abstractmethod
    def create(self, token: OTPTokenEntity) -> OTPTokenEntity:
        ...

    @abstractmethod
    def get_valid_token(
        self, usuario_id: int, codigo: str
    ) -> Optional[OTPTokenEntity]:
        """Return an unused, non-expired token matching usuario + codigo."""
        ...

    @abstractmethod
    def mark_as_used(self, usuario_id: int, codigo: str) -> None:
        ...

    @abstractmethod
    def invalidate_previous(self, usuario_id: int) -> None:
        """Mark all previous tokens for this user as used."""
        ...


class AuditoriaRepository(ABC):
    """Abstract repository for audit log entries."""

    @abstractmethod
    def registrar(self, entry: RegistroAuditoriaEntity) -> None:
        ...

    @abstractmethod
    def listar_por_usuario(
        self, usuario_id: int, limit: int = 50
    ) -> List[RegistroAuditoriaEntity]:
        ...