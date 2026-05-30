"""
Custom password validators for ECPPP.
AD6: Registered in AUTH_PASSWORD_VALIDATORS alongside Django's built-in validators.
"""

import re
import unicodedata

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
            "La contraseña debe contener al menos un símbolo especial " "(por ejemplo: !@#$%^&*)."
        )


def _normalize(text):
    """Lowercase + strip diacritics (NFKD) for accent-insensitive comparison."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    no_diacritics = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return no_diacritics.lower()


class UserAttributeContainmentValidator:
    """Reject passwords containing the user's own data as a substring.

    Compares the password (lowercased, diacritics stripped) against:
        - first_name (and its space-split parts, e.g. "María José" → ["maria", "jose"])
        - last_name (and its space-split parts)
        - email local-part (before the '@')
        - role label (estudiante / docente / inspector / secretaria)

    Tokens shorter than ``min_length`` (default 3) are ignored to avoid
    false positives on very short names ("Li", "Wu").

    Without a ``user`` argument the validator is a no-op — the regular
    Django password validators still run on their own.
    """

    DEFAULT_ATTRIBUTES = ("first_name", "last_name", "email", "rol")

    def __init__(self, user_attributes=DEFAULT_ATTRIBUTES, min_length=3):
        self.user_attributes = user_attributes
        self.min_length = min_length

    def _tokens_for(self, user):
        """Build the set of normalized tokens to check against the password."""
        tokens = set()
        for attr in self.user_attributes:
            raw = getattr(user, attr, "") or ""
            raw = str(raw)
            # Email → use local-part only, ignore the domain.
            if attr == "email" and "@" in raw:
                raw = raw.split("@", 1)[0]
            normalized = _normalize(raw)
            if not normalized:
                continue
            tokens.add(normalized)
            # Split on whitespace to handle compound names ("María José").
            for part in re.split(r"\s+", normalized):
                if part:
                    tokens.add(part)
        return {t for t in tokens if len(t) >= self.min_length}

    def validate(self, password, user=None):
        if user is None:
            return
        normalized_password = _normalize(password)
        if not normalized_password:
            return
        for token in self._tokens_for(user):
            if token in normalized_password:
                raise ValidationError(
                    _("La contraseña no puede contener su nombre, apellido, " "correo o rol."),
                    code="password_contains_user_attribute",
                )

    def get_help_text(self):
        return _("La contraseña no puede contener su nombre, apellido, correo o rol.")
