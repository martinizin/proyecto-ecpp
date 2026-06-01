import pytest
from django.core.exceptions import ValidationError

from apps.core.validators import (
    sanitize_text,
    validate_cedula_ecuatoriana,
    validate_codigo,
    validate_nombre,
    validate_telefono,
)


# ─── validate_nombre ───────────────────────────────────────────────


class TestValidateNombre:
    def test_nombre_simple(self):
        assert validate_nombre("Juan Carlos") == "Juan Carlos"

    def test_nombre_con_tildes(self):
        assert validate_nombre("María José") == "María José"

    def test_nombre_con_guion(self):
        assert validate_nombre("Ana-María") == "Ana-María"

    def test_nombre_con_espacios_alrededor(self):
        assert validate_nombre("  Juan  ") == "Juan"

    def test_nombre_con_numeros_falla(self):
        with pytest.raises(ValidationError, match="solo debe contener letras"):
            validate_nombre("Juan123")

    def test_nombre_un_caracter_falla(self):
        with pytest.raises(ValidationError, match="al menos 2 caracteres"):
            validate_nombre("A")

    def test_nombre_vacio_falla(self):
        with pytest.raises(ValidationError, match="al menos 2 caracteres"):
            validate_nombre("   ")

    def test_nombre_con_caracteres_especiales_falla(self):
        with pytest.raises(ValidationError, match="solo debe contener letras"):
            validate_nombre("Juan@#")

    def test_nombre_con_apostrofe_falla(self):
        with pytest.raises(ValidationError, match="solo debe contener letras"):
            validate_nombre("O'Brien")


# ─── validate_cedula_ecuatoriana ────────────────────────────────────


class TestValidateCedulaEcuatoriana:
    def test_cedula_valida(self):
        assert validate_cedula_ecuatoriana("1710034065") == "1710034065"

    def test_cedula_vacia_permitida(self):
        assert validate_cedula_ecuatoriana("") == ""

    def test_cedula_espacios_vacios(self):
        assert validate_cedula_ecuatoriana("   ") == ""

    def test_cedula_pocos_digitos(self):
        with pytest.raises(ValidationError, match="exactamente 10 dígitos"):
            validate_cedula_ecuatoriana("123")

    def test_cedula_con_letras(self):
        with pytest.raises(ValidationError, match="exactamente 10 dígitos"):
            validate_cedula_ecuatoriana("abcdefghij")

    def test_cedula_provincia_cero(self):
        with pytest.raises(ValidationError, match="código de provincia inválido"):
            validate_cedula_ecuatoriana("0010034065")

    def test_cedula_digito_verificador_incorrecto(self):
        with pytest.raises(ValidationError, match="dígito verificador incorrecto"):
            validate_cedula_ecuatoriana("1710034066")


# ─── validate_telefono ─────────────────────────────────────────────


class TestValidateTelefono:
    def test_telefono_10_digitos_valido(self):
        assert validate_telefono("0991234567") == "0991234567"

    def test_telefono_menos_de_10_digitos_rechazado(self):
        with pytest.raises(ValidationError, match="exactamente 10 dígitos"):
            validate_telefono("123456789")

    def test_telefono_mas_de_10_digitos_rechazado(self):
        with pytest.raises(ValidationError, match="exactamente 10 dígitos"):
            validate_telefono("09912345678")

    def test_telefono_con_letras_rechazado(self):
        with pytest.raises(ValidationError, match="exactamente 10 dígitos"):
            validate_telefono("09912ABC67")

    def test_telefono_con_guion_rechazado(self):
        with pytest.raises(ValidationError, match="exactamente 10 dígitos"):
            validate_telefono("0982525365-1")

    def test_telefono_vacio_permitido(self):
        assert validate_telefono("") == ""


# ─── validate_codigo ───────────────────────────────────────────────


class TestValidateCodigo:
    def test_codigo_con_guion(self):
        assert validate_codigo("MAT-101") == "MAT-101"

    def test_codigo_lowercase_a_uppercase(self):
        assert validate_codigo("leg001") == "LEG001"

    def test_codigo_con_espacio_falla(self):
        with pytest.raises(ValidationError, match="solo debe contener letras"):
            validate_codigo("MAT 101")

    def test_codigo_un_caracter_falla(self):
        with pytest.raises(ValidationError, match="al menos 2 caracteres"):
            validate_codigo("A")


# ─── sanitize_text ─────────────────────────────────────────────────


class TestSanitizeText:
    def test_texto_plano(self):
        assert sanitize_text("Hello world") == "Hello world"

    def test_script_tag_removido(self):
        assert sanitize_text("<script>alert('xss')</script>") == "alert('xss')"

    def test_bold_tag_removido(self):
        assert sanitize_text("<b>Bold</b>") == "Bold"

    def test_texto_vacio(self):
        assert sanitize_text("") == ""

    def test_none_retorna_none(self):
        assert sanitize_text(None) is None
