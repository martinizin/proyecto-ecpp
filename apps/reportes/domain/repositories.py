"""
Repository interfaces for the Reportes bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

from abc import ABC, abstractmethod


class IReporteANTRepository(ABC):
    """Abstract repository for ReporteANT persistence."""

    @abstractmethod
    def guardar(self, reporte_data: dict):
        """Persist a new ANT report record."""

    @abstractmethod
    def listar_por_periodo(self, periodo_id: int):
        """Return all reports for a given period, newest first."""

    @abstractmethod
    def obtener_por_id(self, reporte_id: int):
        """Return a single report by PK, or None."""
