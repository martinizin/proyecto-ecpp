"""
Repository interfaces for the Asistencia bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from abc import ABC, abstractmethod
from typing import List

from .entities import AsistenciaEntity


class AsistenciaRepository(ABC):
    """Abstract repository for Asistencia aggregate."""

    @abstractmethod
    def list_by_paralelo(self, paralelo_id: int) -> List[AsistenciaEntity]:
        ...
