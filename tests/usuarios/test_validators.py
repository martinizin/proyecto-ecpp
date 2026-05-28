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
    UserAttributeContainmentValidator,
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


# =============================================================================
# UserAttributeContainmentValidator Tests (HU21 QA fix 1.1)
# =============================================================================


class _FakeUser:
    """Lightweight stand-in for Usuario — avoids DB hits in pure unit tests."""

    def __init__(self, first_name="", last_name="", email="", rol=""):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.rol = rol


class TestUserAttributeContainmentValidator:
    """Tests for UserAttributeContainmentValidator.

    Rejects passwords that contain the user's first_name, last_name,
    email local-part, or role label as a substring (case- and
    accent-insensitive, ≥3 chars).
    """

    def setup_method(self):
        self.validator = UserAttributeContainmentValidator()

    # --- No user / empty user → never rejects (delegated to other validators) ---

    def test_sin_usuario_no_valida(self):
        """Sin user el validador no rechaza nada (no tiene contra qué comparar)."""
        self.validator.validate("Maria123+", user=None)

    def test_usuario_con_atributos_vacios_no_valida(self):
        user = _FakeUser()
        self.validator.validate("Cualquier123+", user=user)

    # --- Rechaza por first_name / last_name ---

    @pytest.mark.parametrize(
        "password",
        [
            "Maria123+",
            "MARIA_secreta!",
            "xxMariaxx9!",
            "maria2024!",
        ],
    )
    def test_rechaza_password_con_first_name(self, password):
        user = _FakeUser(first_name="María", last_name="Pérez", rol="estudiante")
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password, user=user)
        assert exc_info.value.code == "password_contains_user_attribute"

    def test_rechaza_password_con_last_name(self):
        user = _FakeUser(first_name="Juan", last_name="Gonzalez", rol="docente")
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate("MiPassGonzalez1!", user=user)
        assert exc_info.value.code == "password_contains_user_attribute"

    def test_rechaza_first_name_compuesto_por_partes(self):
        """'María José' → debe rechazar 'jose' como substring."""
        user = _FakeUser(first_name="María José", last_name="Pérez", rol="docente")
        with pytest.raises(ValidationError):
            self.validator.validate("Jose2024!", user=user)

    # --- Rechaza por rol ---

    @pytest.mark.parametrize(
        "rol,password",
        [
            ("estudiante", "Estudiante123!"),
            ("docente", "Docente@2024"),
            ("inspector", "Inspector#9"),
            ("secretaria", "Secretaria123@"),
        ],
    )
    def test_rechaza_password_con_rol(self, rol, password):
        user = _FakeUser(first_name="Ana", last_name="Lopez", rol=rol)
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password, user=user)
        assert exc_info.value.code == "password_contains_user_attribute"

    # --- Rechaza por email local-part ---

    def test_rechaza_password_con_local_part_de_email(self):
        user = _FakeUser(
            first_name="X", last_name="Y", email="jperez@ecppp.edu.ec", rol="docente"
        )
        with pytest.raises(ValidationError):
            self.validator.validate("Jperez@2024!", user=user)

    # --- Insensibilidad a acentos y mayúsculas ---

    def test_normaliza_acentos(self):
        """'María' debe matchear 'maria' en la pass."""
        user = _FakeUser(first_name="María", last_name="X", rol="docente")
        with pytest.raises(ValidationError):
            self.validator.validate("PassMaria9!", user=user)

    def test_normaliza_mayusculas(self):
        user = _FakeUser(first_name="ana", last_name="X", rol="docente")
        with pytest.raises(ValidationError):
            self.validator.validate("ANA12345!", user=user)

    # --- Passwords válidas (no contienen ningún atributo) ---

    @pytest.mark.parametrize(
        "password",
        [
            "X9!kQ2#mZ7&",
            "SuperSegura2024!",
            "Random#Word42",
        ],
    )
    def test_password_sin_atributos_pasa(self, password):
        user = _FakeUser(
            first_name="María", last_name="Pérez", email="mperez@x.com", rol="estudiante"
        )
        self.validator.validate(password, user=user)

    # --- Edge case: atributos cortos (<3 chars) NO se chequean ---

    def test_ignora_atributos_de_menos_de_3_chars(self):
        """Apellidos tipo 'Li' o 'Wu' no deben generar falsos positivos."""
        user = _FakeUser(first_name="Wu", last_name="Li", rol="docente")
        # 'li' aparece en la password pero el last_name es <3 chars → no rechaza
        self.validator.validate("FamiliaLinda9!", user=user)

    def test_get_help_text(self):
        text = self.validator.get_help_text()
        assert "nombre" in text.lower() or "rol" in text.lower()
