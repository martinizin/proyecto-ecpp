"""
Re-export models from infrastructure layer for Django model discovery.
Actual model code lives in apps/reportes/infrastructure/models.py
"""

from apps.reportes.infrastructure.models import ReporteANT  # noqa: F401
