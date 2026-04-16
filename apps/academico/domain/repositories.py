"""
Repository interfaces for the Academico bounded context.
Pure Python — NO Django imports allowed in this layer.
Concrete implementations live in infrastructure/.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import (
    AsignaturaEntity,
    MatriculaEntity,
    ParaleloEntity,
    PeriodoEntity,
    TipoLicenciaEntity,
)


class PeriodoRepository(ABC):
    """Abstract repository for Periodo aggregate."""

    @abstractmethod
    def get_by_id(self, periodo_id: int) -> Optional[PeriodoEntity]:
        ...

    @abstractmethod
    def get_activo(self) -> Optional[PeriodoEntity]:
        ...

    @abstractmethod
    def list_all(self) -> List[PeriodoEntity]:
        ...

    @abstractmethod
    def create(self, entity: PeriodoEntity) -> PeriodoEntity:
        ...

    @abstractmethod
    def update(self, periodo_id: int, entity: PeriodoEntity) -> PeriodoEntity:
        ...

    @abstractmethod
    def activar(self, periodo_id: int) -> None:
        """Activate a period (with select_for_update in implementation)."""
        ...

    @abstractmethod
    def desactivar_todos(self) -> None:
        """Deactivate all periods."""
        ...


class TipoLicenciaRepository(ABC):
    """Abstract repository for TipoLicencia (read-only in Sprint 1)."""

    @abstractmethod
    def get_by_id(self, tipo_id: int) -> Optional[TipoLicenciaEntity]:
        ...

    @abstractmethod
    def get_by_codigo(self, codigo: str) -> Optional[TipoLicenciaEntity]:
        ...

    @abstractmethod
    def list_activos(self) -> List[TipoLicenciaEntity]:
        ...


class AsignaturaRepository(ABC):
    """Abstract repository for Asignatura aggregate."""

    @abstractmethod
    def get_by_id(self, asignatura_id: int) -> Optional[AsignaturaEntity]:
        ...

    @abstractmethod
    def get_by_codigo(self, codigo: str) -> Optional[AsignaturaEntity]:
        ...

    @abstractmethod
    def list_all(self) -> List[AsignaturaEntity]:
        ...

    @abstractmethod
    def create(self, entity: AsignaturaEntity) -> AsignaturaEntity:
        ...

    @abstractmethod
    def update(
        self, asignatura_id: int, entity: AsignaturaEntity
    ) -> AsignaturaEntity:
        ...

    @abstractmethod
    def codigo_exists(self, codigo: str, exclude_id: Optional[int] = None) -> bool:
        ...


class ParaleloRepository(ABC):
    """Abstract repository for Paralelo aggregate."""

    @abstractmethod
    def get_by_id(self, paralelo_id: int) -> Optional[ParaleloEntity]:
        ...

    @abstractmethod
    def list_by_periodo(self, periodo_nombre: str) -> List[ParaleloEntity]:
        ...

    @abstractmethod
    def list_all(self) -> List[ParaleloEntity]:
        ...

    @abstractmethod
    def create(self, entity: ParaleloEntity) -> ParaleloEntity:
        ...

    @abstractmethod
    def update(
        self, paralelo_id: int, entity: ParaleloEntity
    ) -> ParaleloEntity:
        ...

    @abstractmethod
    def exists(
        self,
        periodo_id: int,
        tipo_licencia_id: int,
        asignatura_id: int,
        nombre: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Check if a paralelo with the same unique combo already exists."""
        ...


class MatriculaRepository(ABC):
    """Abstract repository for Matricula aggregate."""

    @abstractmethod
    def crear(self, entity: MatriculaEntity) -> MatriculaEntity:
        ...

    @abstractmethod
    def cambiar_estado(self, matricula_id: int, nuevo_estado: str) -> MatriculaEntity:
        ...

    @abstractmethod
    def get_by_estudiante_paralelo(
        self, estudiante_id: int, paralelo_id: int
    ) -> Optional[MatriculaEntity]:
        ...

    @abstractmethod
    def contar_activas_en_paralelo(self, paralelo_id: int) -> int:
        """Count active enrollments in a paralelo (for capacity validation)."""
        ...
