"""
Integration tests for Usuarios application services.
Tests: RegistroAppService, LoginAppService, PerfilAppService.
Requires database. Email services are mocked.
Refs: SCN-AUTH-01→10, SCN-PROF-01→08
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.utils import timezone

from apps.usuarios.application.services import (
    LoginAppService,
    PerfilAppService,
    RegistroAppService,
)
from apps.usuarios.domain.exceptions import (
    CedulaDuplicadaError,
    CorreoDuplicadoError,
    CuentaBloqueadaError,
    OTPInvalidoError,
)
from apps.usuarios.infrastructure.models import (
    OTPToken,
    RegistroAuditoria,
    Usuario,
)


# =============================================================================
# RegistroAppService Tests
# =============================================================================


@pytest.mark.django_db
class TestRegistroAppService:
    """Integration tests for user registration flow."""

    def setup_method(self):
        self.service = RegistroAppService()

    @patch("apps.usuarios.application.services.send_otp_email")
    def test_registrar_exitoso(self, mock_send_otp):
        """Successful registration creates inactive user, OTP token, and sends email."""
        user_id = self.service.registrar(
            username="nuevo_user",
            email="nuevo@test.com",
            password="SecurePass123!",
            first_name="Ana",
            last_name="Torres",
            rol="estudiante",
            cedula="0102030405",
            telefono="0991234567",
            direccion="Quito, Ecuador",
        )

        # User created and inactive
        user = Usuario.objects.get(pk=user_id)
        assert user.username == "nuevo_user"
        assert user.email == "nuevo@test.com"
        assert user.first_name == "Ana"
        assert user.last_name == "Torres"
        assert user.rol == "estudiante"
        assert user.cedula == "0102030405"
        assert user.telefono == "0991234567"
        assert user.direccion == "Quito, Ecuador"
        assert user.is_active is False

        # OTP token created in DB
        otp = OTPToken.objects.filter(usuario=user, usado=False)
        assert otp.exists()
        assert len(otp.first().codigo) == 6

        # Email was sent with user and code
        mock_send_otp.assert_called_once()
        call_args = mock_send_otp.call_args
        assert call_args[0][0].pk == user_id  # first positional arg is user
        assert len(call_args[0][1]) == 6  # second positional arg is codigo

    @patch("apps.usuarios.application.services.send_otp_email")
    def test_registrar_email_duplicado(self, mock_send_otp):
        """Registration with existing email raises CorreoDuplicadoError."""
        Usuario.objects.create_user(
            username="existente",
            email="duplicado@test.com",
            password="TestPass123!",
            rol="estudiante",
        )

        with pytest.raises(CorreoDuplicadoError, match="ya está registrado"):
            self.service.registrar(
                username="otro_user",
                email="duplicado@test.com",
                password="SecurePass123!",
                first_name="Pedro",
                last_name="Lopez",
                rol="docente",
            )

        mock_send_otp.assert_not_called()

    @patch("apps.usuarios.application.services.send_otp_email")
    def test_registrar_cedula_duplicada(self, mock_send_otp):
        """Registration with existing cedula raises CedulaDuplicadaError."""
        Usuario.objects.create_user(
            username="existente",
            email="existente@test.com",
            password="TestPass123!",
            rol="estudiante",
            cedula="0102030405",
        )

        with pytest.raises(CedulaDuplicadaError, match="ya está registrada"):
            self.service.registrar(
                username="otro_user",
                email="otro@test.com",
                password="SecurePass123!",
                first_name="Pedro",
                last_name="Lopez",
                rol="docente",
                cedula="0102030405",
            )

        mock_send_otp.assert_not_called()

    @patch("apps.usuarios.application.services.send_otp_email")
    def test_verificar_otp_exitoso(self, mock_send_otp):
        """Valid OTP verification activates the user account."""
        # Create inactive user
        user = Usuario.objects.create_user(
            username="otp_user",
            email="otp@test.com",
            password="TestPass123!",
            rol="estudiante",
            is_active=False,
        )

        # Create OTP token manually
        codigo = "123456"
        OTPToken.objects.create(
            usuario=user,
            codigo=codigo,
            expira_en=timezone.now() + timedelta(minutes=10),
            usado=False,
        )

        # Verify OTP
        self.service.verificar_otp(user_id=user.pk, codigo=codigo)

        # User is now active
        user.refresh_from_db()
        assert user.is_active is True

        # OTP token marked as used
        otp = OTPToken.objects.get(usuario=user, codigo=codigo)
        assert otp.usado is True

    @patch("apps.usuarios.application.services.send_otp_email")
    def test_verificar_otp_codigo_incorrecto(self, mock_send_otp):
        """Invalid OTP code raises OTPInvalidoError."""
        # Create inactive user
        user = Usuario.objects.create_user(
            username="otp_user",
            email="otp@test.com",
            password="TestPass123!",
            rol="estudiante",
            is_active=False,
        )

        # Create OTP token
        OTPToken.objects.create(
            usuario=user,
            codigo="123456",
            expira_en=timezone.now() + timedelta(minutes=10),
            usado=False,
        )

        # Try with wrong code
        with pytest.raises(OTPInvalidoError, match="incorrecto"):
            self.service.verificar_otp(user_id=user.pk, codigo="000000")

        # User should still be inactive
        user.refresh_from_db()
        assert user.is_active is False


# =============================================================================
# LoginAppService Tests
# =============================================================================


@pytest.mark.django_db
class TestLoginAppService:
    """Integration tests for login flow with lockout and audit."""

    def setup_method(self):
        self.service = LoginAppService()
        self.password = "TestPass123!"
        self.user = Usuario.objects.create_user(
            username="login_user",
            email="login@test.com",
            password=self.password,
            first_name="Carlos",
            last_name="Ruiz",
            rol="inspector",
            is_active=True,
        )

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_login_exitoso(self, mock_lockout_email):
        """Successful login returns user, resets attempts, creates audit."""
        result = self.service.intentar_login(
            email="login@test.com",
            password=self.password,
            tipo_usuario="inspector",
            ip="192.168.1.1",
        )

        assert result is not None
        assert result.pk == self.user.pk

        # Failed attempts reset to 0
        self.user.refresh_from_db()
        assert self.user.intentos_fallidos == 0
        assert self.user.bloqueado_hasta is None

        # Audit record created
        audit = RegistroAuditoria.objects.filter(
            usuario=self.user, accion="login_exitoso"
        )
        assert audit.exists()
        assert "inspector" in audit.first().detalle

        mock_lockout_email.assert_not_called()

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_login_password_incorrecto(self, mock_lockout_email):
        """Wrong password returns None and increments failed attempts."""
        result = self.service.intentar_login(
            email="login@test.com",
            password="WrongPassword!",
            tipo_usuario="inspector",
            ip="192.168.1.1",
        )

        assert result is None

        # Failed attempts incremented
        self.user.refresh_from_db()
        assert self.user.intentos_fallidos == 1
        assert self.user.bloqueado_hasta is None

        # Audit record for failed attempt
        audit = RegistroAuditoria.objects.filter(
            usuario=self.user, accion="login_fallido"
        )
        assert audit.exists()

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_login_tipo_usuario_incorrecto(self, mock_lockout_email):
        """Correct credentials but wrong role returns None."""
        result = self.service.intentar_login(
            email="login@test.com",
            password=self.password,
            tipo_usuario="estudiante",  # User is inspector, not estudiante
            ip="192.168.1.1",
        )

        assert result is None

        # Failed attempts incremented
        self.user.refresh_from_db()
        assert self.user.intentos_fallidos == 1

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_login_email_no_existe(self, mock_lockout_email):
        """Non-existent email returns None and creates audit record."""
        result = self.service.intentar_login(
            email="noexiste@test.com",
            password=self.password,
            tipo_usuario="inspector",
            ip="10.0.0.1",
        )

        assert result is None

        # Audit record for failed attempt (no user)
        audit = RegistroAuditoria.objects.filter(
            accion="login_fallido", usuario__isnull=True
        )
        assert audit.exists()
        assert "noexiste@test.com" in audit.first().detalle

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_login_bloqueo_tras_max_intentos(self, mock_lockout_email):
        """After MAX_LOGIN_ATTEMPTS failures, account is locked."""
        max_attempts = settings.MAX_LOGIN_ATTEMPTS  # 5

        for i in range(max_attempts):
            self.service.intentar_login(
                email="login@test.com",
                password="WrongPassword!",
                tipo_usuario="inspector",
                ip="192.168.1.1",
            )

        # Check DB state
        self.user.refresh_from_db()
        assert self.user.intentos_fallidos == max_attempts
        assert self.user.bloqueado_hasta is not None
        assert self.user.bloqueado_hasta > timezone.now()

        # Lockout notification was sent
        mock_lockout_email.assert_called_once()

        # Audit records: bloqueo action exists
        audit_bloqueo = RegistroAuditoria.objects.filter(
            usuario=self.user, accion="bloqueo"
        )
        assert audit_bloqueo.exists()

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_login_cuenta_bloqueada(self, mock_lockout_email):
        """Login attempt on locked account raises CuentaBloqueadaError."""
        # Lock the account directly
        self.user.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
        self.user.intentos_fallidos = settings.MAX_LOGIN_ATTEMPTS
        self.user.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])

        with pytest.raises(CuentaBloqueadaError, match="bloqueada"):
            self.service.intentar_login(
                email="login@test.com",
                password=self.password,
                tipo_usuario="inspector",
                ip="192.168.1.1",
            )


# =============================================================================
# PerfilAppService Tests
# =============================================================================


@pytest.mark.django_db
class TestPerfilAppService:
    """Integration tests for profile management."""

    def setup_method(self):
        self.service = PerfilAppService()
        self.password = "TestPass123!"
        self.user = Usuario.objects.create_user(
            username="perfil_user",
            email="perfil@test.com",
            password=self.password,
            first_name="Maria",
            last_name="Garcia",
            rol="docente",
            telefono="0991111111",
            direccion="Guayaquil, Ecuador",
            is_active=True,
        )

    def test_actualizar_datos(self):
        """Profile data fields are updated in the database."""
        self.service.actualizar_datos(
            user_id=self.user.pk,
            first_name="Maria Jose",
            last_name="Garcia Torres",
            telefono="0999999999",
            direccion="Cuenca, Ecuador",
        )

        self.user.refresh_from_db()
        assert self.user.first_name == "Maria Jose"
        assert self.user.last_name == "Garcia Torres"
        assert self.user.telefono == "0999999999"
        assert self.user.direccion == "Cuenca, Ecuador"

    def test_cambiar_contrasena_exitoso(self):
        """Correct old password allows password change, returns True."""
        new_password = "NewSecure456!"
        result = self.service.cambiar_contrasena(
            user_id=self.user.pk,
            old_password=self.password,
            new_password=new_password,
        )

        assert result is True

        # New password works
        self.user.refresh_from_db()
        assert self.user.check_password(new_password) is True
        assert self.user.check_password(self.password) is False

    def test_cambiar_contrasena_password_incorrecto(self):
        """Wrong old password returns False, password unchanged."""
        result = self.service.cambiar_contrasena(
            user_id=self.user.pk,
            old_password="WrongOldPass!",
            new_password="NewSecure456!",
        )

        assert result is False

        # Original password still works
        self.user.refresh_from_db()
        assert self.user.check_password(self.password) is True
