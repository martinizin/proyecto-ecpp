"""
Repository interfaces for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure. Concrete implementations live in infrastructure/.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .entities import UsuarioEntity


class UsuarioRepository(ABC):
    """Abstract repository for Usuario aggregate."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[UsuarioEntity]:
        ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UsuarioEntity]:
        ...
