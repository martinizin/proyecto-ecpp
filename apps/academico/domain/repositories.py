"""
Repository interfaces for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import AsignaturaEntity, ParaleloEntity, PeriodoEntity


class PeriodoRepository(ABC):
    """Abstract repository for Periodo aggregate."""

    @abstractmethod
    def get_activo(self) -> Optional[PeriodoEntity]:
        ...


class AsignaturaRepository(ABC):
    """Abstract repository for Asignatura aggregate."""

    @abstractmethod
    def get_by_codigo(self, codigo: str) -> Optional[AsignaturaEntity]:
        ...


class ParaleloRepository(ABC):
    """Abstract repository for Paralelo aggregate."""

    @abstractmethod
    def list_by_periodo(self, periodo_nombre: str) -> List[ParaleloEntity]:
        ...
