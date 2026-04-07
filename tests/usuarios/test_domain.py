"""
Unit tests for Usuarios domain layer.
Pure Python — NO database required.
Tests: OTPService, LoginService, RegistroService, Cedula (modulo-10), Email.
Refs: SCN-AUTH-01→10
"""

from datetime import datetime, timedelta

import pytest

from apps.usuarios.domain.exceptions import (
    CedulaDuplicadaError,
    CorreoDuplicadoError,
    CuentaBloqueadaError,
    OTPExpiradoError,
    OTPInvalidoError,
)
from apps.usuarios.domain.services import LoginService, OTPService, RegistroService
from apps.usuarios.domain.value_objects import Cedula, Email


# =============================================================================
# Cedula (modulo-10) Tests
# =============================================================================


class TestCedula:
    """Tests for Ecuadorian cédula validation (modulo-10 algorithm)."""

    @pytest.mark.parametrize(
        "cedula",
        [
            "0102030405",
            "1710034065",
            "0926687856",
        ],
    )
    def test_cedula_valida(self, cedula):
        vo = Cedula(valor=cedula)
        assert vo.valor == cedula

    def test_cedula_vacia_permitida(self):
        """Empty cedula is allowed (field is optional)."""
        vo = Cedula(valor="")
        assert vo.valor == ""

    def test_cedula_no_numerica(self):
        with pytest.raises(ValueError, match="10 dígitos numéricos"):
            Cedula(valor="ABC1234567")

    def test_cedula_longitud_incorrecta(self):
        with pytest.raises(ValueError, match="10 dígitos numéricos"):
            Cedula(valor="12345")

    def test_cedula_provincia_invalida_00(self):
        with pytest.raises(ValueError, match="provincia válida"):
            Cedula(valor="0012345678")

    def test_cedula_provincia_invalida_25(self):
        with pytest.raises(ValueError, match="provincia válida"):
            Cedula(valor="2512345678")

    def test_cedula_digito_verificador_incorrecto(self):
        with pytest.raises(ValueError, match="módulo 10"):
            Cedula(valor="0102030406")  # Last digit wrong

    @pytest.mark.parametrize(
        "cedula",
        [
            "9999999999",
            "0100000000",
        ],
    )
    def test_cedulas_inventadas_invalidas(self, cedula):
        with pytest.raises(ValueError):
            Cedula(valor=cedula)


# =============================================================================
# Email Tests
# =============================================================================


class TestEmail:
    """Tests for Email value object."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "test.user@domain.org",
            "name+tag@sub.domain.co",
        ],
    )
    def test_email_valido(self, email):
        vo = Email(valor=email)
        assert vo.valor == email

    def test_email_vacio_rechazado(self):
        with pytest.raises(ValueError, match="obligatorio"):
            Email(valor="")

    @pytest.mark.parametrize(
        "email",
        [
            "noarroba.com",
            "@sinusuario.com",
            "user@",
            "user@.com",
            "user @domain.com",
        ],
    )
    def test_email_formato_invalido(self, email):
        with pytest.raises(ValueError, match="no es válido"):
            Email(valor=email)


# =============================================================================
# OTPService Tests
# =============================================================================


class TestOTPService:
    """Tests for OTP generation and verification."""

    def setup_method(self):
        self.service = OTPService()
        self.now = datetime(2026, 4, 1, 12, 0, 0)

    def test_generar_codigo_6_digitos(self):
        codigo, _ = self.service.generar(
            usuario_id=1, now=self.now, expiration_minutes=10
        )
        assert len(codigo) == 6
        assert codigo.isdigit()

    def test_generar_expiracion_correcta(self):
        _, expira_en = self.service.generar(
            usuario_id=1, now=self.now, expiration_minutes=10
        )
        assert expira_en == self.now + timedelta(minutes=10)

    def test_generar_codigos_diferentes(self):
        """Two consecutive generations should (almost always) produce different codes."""
        codigos = set()
        for _ in range(20):
            codigo, _ = self.service.generar(
                usuario_id=1, now=self.now, expiration_minutes=10
            )
            codigos.add(codigo)
        # With 20 attempts and 1M possible codes, collision is extremely unlikely
        assert len(codigos) > 1

    def test_verificar_exitoso(self):
        """Valid code within expiration should pass without exception."""
        self.service.verificar(
            codigo_ingresado="123456",
            codigo_almacenado="123456",
            expira_en=self.now + timedelta(minutes=10),
            usado=False,
            now=self.now,
        )

    def test_verificar_codigo_incorrecto(self):
        with pytest.raises(OTPInvalidoError, match="incorrecto"):
            self.service.verificar(
                codigo_ingresado="000000",
                codigo_almacenado="123456",
                expira_en=self.now + timedelta(minutes=10),
                usado=False,
                now=self.now,
            )

    def test_verificar_codigo_expirado(self):
        with pytest.raises(OTPExpiradoError, match="expirado"):
            self.service.verificar(
                codigo_ingresado="123456",
                codigo_almacenado="123456",
                expira_en=self.now - timedelta(minutes=1),
                usado=False,
                now=self.now,
            )

    def test_verificar_codigo_ya_usado(self):
        with pytest.raises(OTPInvalidoError, match="ya fue utilizado"):
            self.service.verificar(
                codigo_ingresado="123456",
                codigo_almacenado="123456",
                expira_en=self.now + timedelta(minutes=10),
                usado=True,
                now=self.now,
            )

    def test_verificar_usado_tiene_prioridad_sobre_expirado(self):
        """If code is already used, that error should come first."""
        with pytest.raises(OTPInvalidoError, match="ya fue utilizado"):
            self.service.verificar(
                codigo_ingresado="123456",
                codigo_almacenado="123456",
                expira_en=self.now - timedelta(minutes=1),
                usado=True,
                now=self.now,
            )


# =============================================================================
# LoginService Tests
# =============================================================================


class TestLoginService:
    """Tests for login lockout logic."""

    def setup_method(self):
        self.service = LoginService()
        self.now = datetime(2026, 4, 1, 12, 0, 0)

    def test_verificar_bloqueo_sin_bloqueo(self):
        """No lockout — should pass without exception."""
        self.service.verificar_bloqueo(bloqueado_hasta=None, now=self.now)

    def test_verificar_bloqueo_expirado(self):
        """Lockout has expired — should pass."""
        pasado = self.now - timedelta(minutes=1)
        self.service.verificar_bloqueo(bloqueado_hasta=pasado, now=self.now)

    def test_verificar_bloqueo_activo(self):
        """Lockout is active — should raise."""
        futuro = self.now + timedelta(minutes=10)
        with pytest.raises(CuentaBloqueadaError, match="bloqueada"):
            self.service.verificar_bloqueo(bloqueado_hasta=futuro, now=self.now)

    def test_verificar_bloqueo_mensaje_minutos(self):
        """Error message should include minutes remaining."""
        futuro = self.now + timedelta(minutes=5)
        with pytest.raises(CuentaBloqueadaError, match="6 minuto"):
            self.service.verificar_bloqueo(bloqueado_hasta=futuro, now=self.now)

    @pytest.mark.parametrize(
        "intentos,max_intentos,expected_count,should_lock",
        [
            (0, 5, 1, False),
            (1, 5, 2, False),
            (3, 5, 4, False),
            (4, 5, 5, True),   # 5th attempt → lock
            (9, 5, 10, True),  # Already over max → lock
        ],
    )
    def test_registrar_intento_fallido(
        self, intentos, max_intentos, expected_count, should_lock
    ):
        count, bloqueado = self.service.registrar_intento_fallido(
            intentos_fallidos=intentos,
            max_intentos=max_intentos,
            lockout_minutes=15,
            now=self.now,
        )
        assert count == expected_count
        if should_lock:
            assert bloqueado == self.now + timedelta(minutes=15)
        else:
            assert bloqueado is None

    def test_resetear_intentos(self):
        count, bloqueado = self.service.resetear_intentos()
        assert count == 0
        assert bloqueado is None


# =============================================================================
# RegistroService Tests
# =============================================================================


class TestRegistroService:
    """Tests for registration domain validation."""

    def setup_method(self):
        self.service = RegistroService()

    def test_validar_datos_exitoso(self):
        """Valid data should pass without exception."""
        self.service.validar_datos_registro(
            email="nuevo@test.com",
            cedula="0102030405",
            email_exists=False,
            cedula_exists=False,
        )

    def test_validar_email_duplicado(self):
        with pytest.raises(CorreoDuplicadoError, match="ya está registrado"):
            self.service.validar_datos_registro(
                email="existe@test.com",
                cedula="0102030405",
                email_exists=True,
                cedula_exists=False,
            )

    def test_validar_cedula_duplicada(self):
        with pytest.raises(CedulaDuplicadaError, match="ya está registrada"):
            self.service.validar_datos_registro(
                email="nuevo@test.com",
                cedula="0102030405",
                email_exists=False,
                cedula_exists=True,
            )

    def test_validar_cedula_vacia_no_verifica_duplicado(self):
        """Empty cedula should not trigger duplicate check."""
        self.service.validar_datos_registro(
            email="nuevo@test.com",
            cedula="",
            email_exists=False,
            cedula_exists=True,  # Should be ignored because cedula is empty
        )

    def test_validar_email_formato_invalido(self):
        with pytest.raises(ValueError, match="no es válido"):
            self.service.validar_datos_registro(
                email="no-es-email",
                cedula="",
                email_exists=False,
                cedula_exists=False,
            )

    def test_validar_cedula_formato_invalido(self):
        with pytest.raises(ValueError, match="10 dígitos"):
            self.service.validar_datos_registro(
                email="user@test.com",
                cedula="12345",
                email_exists=False,
                cedula_exists=False,
            )
