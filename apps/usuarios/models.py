"""
Re-export models from infrastructure layer for Django model discovery.
Actual model code lives in apps/usuarios/infrastructure/models.py
"""

from apps.usuarios.infrastructure.models import *  # noqa: F401, F403
