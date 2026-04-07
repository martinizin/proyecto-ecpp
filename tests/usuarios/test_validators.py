"""
Unit tests for custom password validators.
Tests: UppercaseValidator, SymbolValidator.
Ref: AC-AUTH-03, AD6
"""

import pytest
from django.core.exceptions import ValidationError

from apps.usuarios.infrastructure.password_validators import (
    SymbolValidator,
    UppercaseValidator,
)


# =============================================================================
# UppercaseValidator Tests
# =============================================================================


class TestUppercaseValidator:
    """Tests for UppercaseValidator."""

    def setup_method(self):
        self.validator = UppercaseValidator()

    @pytest.mark.parametrize(
        "password",
        [
            "Abcdef123!",
            "testPASS1!",
            "A",
            "123456A!",
            "hola Mundo",
        ],
    )
    def test_password_con_mayuscula_valida(self, password):
        """Passwords with at least one uppercase should pass."""
        self.validator.validate(password)

    @pytest.mark.parametrize(
        "password",
        [
            "abcdef123!",
            "sin mayusculas",
            "123456789!",
            "todo minuscula!@#",
        ],
    )
    def test_password_sin_mayuscula_rechazada(self, password):
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        assert exc_info.value.code == "password_no_uppercase"

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "mayúscula" in text


# =============================================================================
# SymbolValidator Tests
# =============================================================================


class TestSymbolValidator:
    """Tests for SymbolValidator."""

    def setup_method(self):
        self.validator = SymbolValidator()

    @pytest.mark.parametrize(
        "password",
        [
            "Abcdef123!",
            "test@pass",
            "hola#mundo",
            "pass$word",
            "one%two",
            "a^b",
            "a&b",
            "a*b",
            "a(b",
            "a)b",
            "a-b",
            "a_b",
            "a+b",
            "a=b",
            "a[b",
            "a{b",
            "a;b",
            "a'b",
            'a"b',
            "a|b",
            "a,b",
            "a.b",
            "a<b",
            "a/b",
            "a?b",
            "a`b",
            "a~b",
        ],
    )
    def test_password_con_simbolo_valida(self, password):
        """Passwords with at least one symbol should pass."""
        self.validator.validate(password)

    @pytest.mark.parametrize(
        "password",
        [
            "Abcdef123",
            "SoloLetrasYNumeros9",
            "PURO TEXTO",
            "123456789",
        ],
    )
    def test_password_sin_simbolo_rechazada(self, password):
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        assert exc_info.value.code == "password_no_symbol"

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "símbolo" in text
