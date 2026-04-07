"""
Re-export models from infrastructure layer for Django model discovery.
Actual model code lives in apps/academico/infrastructure/models.py
"""

from apps.academico.infrastructure.models import (  # noqa: F401
    Asignatura,
    Paralelo,
    Periodo,
    TipoLicencia,
)
