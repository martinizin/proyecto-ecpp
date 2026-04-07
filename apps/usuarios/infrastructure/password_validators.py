"""
Custom password validators for ECPPP.
AD6: Registered in AUTH_PASSWORD_VALIDATORS alongside Django's built-in validators.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class UppercaseValidator:
    """Validate that the password contains at least one uppercase letter."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("La contraseña debe contener al menos una letra mayúscula."),
                code="password_no_uppercase",
            )

    def get_help_text(self):
        return _("La contraseña debe contener al menos una letra mayúscula.")


class SymbolValidator:
    """Validate that the password contains at least one special symbol."""

    SYMBOLS = r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]"

    def validate(self, password, user=None):
        if not re.search(self.SYMBOLS, password):
            raise ValidationError(
                _("La contraseña debe contener al menos un símbolo especial."),
                code="password_no_symbol",
            )

    def get_help_text(self):
        return _(
            "La contraseña debe contener al menos un símbolo especial "
            "(por ejemplo: !@#$%^&*)."
        )
