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


class CedulaObligatoriaError(UsuarioError):
    """Raised when a user is created without a cédula (required post-immutability)."""


class UsuarioConDependenciasError(UsuarioError):
    """
    Raised by `eliminar_usuario` when the target user still has FK dependencies
    (matrículas, asistencias, solicitudes, calificaciones, notificaciones).

    Carries a per-entity count dict so the presentation layer can render a
    friendly breakdown to the secretaría. The message includes the grand total.
    """

    def __init__(self, dependencias: dict[str, int]):
        self.dependencias = dependencias
        total = sum(dependencias.values())
        super().__init__(f"El usuario tiene {total} dependencia(s) y no puede ser eliminado.")
