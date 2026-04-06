"""
Repository interfaces for the Calificaciones bounded context.
Pure Python — NO Django imports allowed in this layer.

Sprint 0: Placeholder structure.
"""

from abc import ABC, abstractmethod


class EvaluacionRepository(ABC):
    """Abstract repository for Evaluacion aggregate."""

    @abstractmethod
    def get_by_paralelo(self, paralelo_id: int) -> list:
        ...


class CalificacionRepository(ABC):
    """Abstract repository for Calificacion aggregate."""

    @abstractmethod
    def get_by_evaluacion(self, evaluacion_id: int) -> list:
        ...
