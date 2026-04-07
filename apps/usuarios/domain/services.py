"""
Domain services for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.

Services encapsulate domain rules that don't belong to a single entity.
They receive data and repository interfaces, never ORM models.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from .exceptions import (
    CedulaDuplicadaError,
    CorreoDuplicadoError,
    CuentaBloqueadaError,
    OTPExpiradoError,
    OTPInvalidoError,
)
from .value_objects import Cedula, Email


class RegistroService:
    """
    Domain rules for user registration.
    Validates uniqueness of cedula/email and password policy compliance.
    """

    def validar_datos_registro(
        self,
        email: str,
        cedula: str,
        email_exists: bool,
        cedula_exists: bool,
    ) -> None:
        """
        Validate registration data at the domain level.
        Raises domain exceptions if business rules are violated.
        """
        # Validate value objects (format)
        Email(valor=email)
        if cedula:
            Cedula(valor=cedula)

        # Uniqueness rules
        if email_exists:
            raise CorreoDuplicadoError(
                f"El correo electrónico '{email}' ya está registrado."
            )
        if cedula and cedula_exists:
            raise CedulaDuplicadaError(
                f"La cédula '{cedula}' ya está registrada."
            )


class LoginService:
    """
    Domain rules for login: lockout check and attempt counting.
    """

    def verificar_bloqueo(
        self,
        bloqueado_hasta: Optional[datetime],
        now: datetime,
    ) -> None:
        """
        Check if the account is currently locked.
        Raises CuentaBloqueadaError if locked.
        """
        if bloqueado_hasta and bloqueado_hasta > now:
            minutos_restantes = int(
                (bloqueado_hasta - now).total_seconds() / 60
            )
            raise CuentaBloqueadaError(
                f"Cuenta bloqueada. Intente nuevamente en {minutos_restantes + 1} minuto(s)."
            )

    def registrar_intento_fallido(
        self,
        intentos_fallidos: int,
        max_intentos: int,
        lockout_minutes: int,
        now: datetime,
    ) -> tuple[int, Optional[datetime]]:
        """
        Register a failed login attempt.

        Returns:
            (new_attempt_count, bloqueado_hasta or None)
        """
        nuevos_intentos = intentos_fallidos + 1

        if nuevos_intentos >= max_intentos:
            bloqueado_hasta = now + timedelta(minutes=lockout_minutes)
            return nuevos_intentos, bloqueado_hasta

        return nuevos_intentos, None

    def resetear_intentos(self) -> tuple[int, None]:
        """Reset failed attempts after a successful login."""
        return 0, None


class OTPService:
    """
    Domain rules for OTP generation and verification.
    """

    def generar(
        self,
        usuario_id: int,
        now: datetime,
        expiration_minutes: int,
    ) -> tuple[str, datetime]:
        """
        Generate a 6-digit OTP code.

        Returns:
            (codigo, expira_en)
        """
        codigo = "".join(random.choices(string.digits, k=6))
        expira_en = now + timedelta(minutes=expiration_minutes)
        return codigo, expira_en

    def verificar(
        self,
        codigo_ingresado: str,
        codigo_almacenado: str,
        expira_en: datetime,
        usado: bool,
        now: datetime,
    ) -> None:
        """
        Verify an OTP code. Raises domain exceptions on failure.
        """
        if usado:
            raise OTPInvalidoError("Este código OTP ya fue utilizado.")

        if now > expira_en:
            raise OTPExpiradoError(
                "El código OTP ha expirado. Solicite uno nuevo."
            )

        if codigo_ingresado != codigo_almacenado:
            raise OTPInvalidoError("El código OTP ingresado es incorrecto.")
