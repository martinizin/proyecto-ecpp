"""
Repository interfaces for the Solicitudes bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from abc import ABC, abstractmethod
from typing import List

from .entities import SolicitudEntity


class SolicitudRepository(ABC):
    """Abstract repository for Solicitud aggregate."""

    @abstractmethod
    def list_pendientes(self) -> List[SolicitudEntity]:
        ...
