"""
Value objects for the Usuarios bounded context.
Pure Python — NO Django imports allowed in this layer.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Cedula:
    """
    Ecuadorian identification number (cédula).
    Validates format (10 digits) and modulo-10 check digit.
    """

    valor: str

    def __post_init__(self) -> None:
        if not self.valor:
            return  # Allow empty — field is optional

        if not re.fullmatch(r"\d{10}", self.valor):
            raise ValueError(
                "La cédula debe contener exactamente 10 dígitos numéricos."
            )

        provincia = int(self.valor[:2])
        if provincia < 1 or provincia > 24:
            raise ValueError(
                "Los dos primeros dígitos deben corresponder a una provincia válida (01-24)."
            )

        if not self._validar_modulo_10(self.valor):
            raise ValueError("La cédula no pasa la validación módulo 10.")

    @staticmethod
    def _validar_modulo_10(cedula: str) -> bool:
        """
        Modulo-10 algorithm for Ecuadorian cédula validation.
        - Multiply odd-position digits by 2; subtract 9 if result > 9.
        - Sum all digits.
        - Check digit = (next multiple of 10 - sum) mod 10.
        """
        coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        suma = 0

        for i in range(9):
            producto = int(cedula[i]) * coeficientes[i]
            if producto > 9:
                producto -= 9
            suma += producto

        verificador = (10 - (suma % 10)) % 10
        return verificador == int(cedula[9])


@dataclass(frozen=True)
class Email:
    """
    Email value object with basic format validation.
    Does not verify deliverability — only structure.
    """

    valor: str

    _EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    def __post_init__(self) -> None:
        if not self.valor:
            raise ValueError("El correo electrónico es obligatorio.")

        if not self._EMAIL_REGEX.fullmatch(self.valor):
            raise ValueError(
                f"El formato del correo electrónico '{self.valor}' no es válido."
            )
