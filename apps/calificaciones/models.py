"""
Re-export models from infrastructure layer for Django model discovery.
Actual model code lives in apps/calificaciones/infrastructure/models.py
"""

from apps.calificaciones.infrastructure.models import *  # noqa: F401, F403
