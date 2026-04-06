"""
Domain-specific exceptions for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.
"""


class UsuarioError(Exception):
    """Base exception for Usuario domain errors."""


class RolInvalidoError(UsuarioError):
    """Raised when an invalid role is assigned."""


class CedulaDuplicadaError(UsuarioError):
    """Raised when a duplicate cedula is detected."""
