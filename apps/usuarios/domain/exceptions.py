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


class CorreoDuplicadoError(UsuarioError):
    """Raised when a duplicate email is detected during registration."""


class CuentaBloqueadaError(UsuarioError):
    """Raised when a login attempt is made on a locked account."""


class OTPExpiradoError(UsuarioError):
    """Raised when an OTP code has expired."""


class OTPInvalidoError(UsuarioError):
    """Raised when an OTP code is incorrect or already used."""
