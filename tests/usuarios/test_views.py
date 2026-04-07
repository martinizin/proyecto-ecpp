"""
View tests for the Usuarios bounded context using Django test Client.

Tests: RegistroView, VerificacionOTPView, LoginView, LogoutView,
       DashboardRedirectView, PerfilView, CambiarContrasenaView,
       PasswordRecovery.
Refs: HU01→HU04, SCN-AUTH-01→10, SCN-PROF-01→08
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.infrastructure.models import OTPToken, Usuario

AUTH_BACKEND = "apps.usuarios.infrastructure.auth_backend.ECPPPAuthBackend"
PASSWORD = "SecurePass123!"


def _create_active_user(
    email: str,
    rol: str = "estudiante",
    password: str = PASSWORD,
    **kwargs,
) -> Usuario:
    """Helper: create an active user ready for login."""
    defaults = {
        "username": email,
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "rol": rol,
        "is_active": True,
    }
    defaults.update(kwargs)
    return Usuario.objects.create_user(**defaults)


# =============================================================================
# TestRegistroView — 3 tests
# =============================================================================


@pytest.mark.django_db
class TestRegistroView:
    """View tests for user registration (HU01)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:registro")

    def test_get_registro_page(self):
        """GET /usuarios/registro/ returns 200 and uses correct template."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/registro.html" in [t.name for t in response.templates]

    @patch("apps.usuarios.application.services.send_otp_email")
    def test_post_registro_exitoso(self, mock_send_otp):
        """POST valid data → redirects to verificar_otp, session has otp_user_id."""
        data = {
            "first_name": "Ana",
            "last_name": "Torres",
            "email": "ana@test.com",
            "cedula": "0102030405",
            "telefono": "0991234567",
            "rol": "estudiante",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }

        response = self.client.post(self.url, data)

        # Redirects to OTP verification
        assert response.status_code == 302
        assert response.url == reverse("usuarios:verificar_otp")

        # User created as inactive
        user = Usuario.objects.get(email="ana@test.com")
        assert user.is_active is False
        assert user.first_name == "Ana"
        assert user.rol == "estudiante"

        # OTP user_id stored in session
        session = self.client.session
        assert "otp_user_id" in session
        assert session["otp_user_id"] == user.pk

        # OTP email was sent
        mock_send_otp.assert_called_once()

    def test_post_registro_form_invalido(self):
        """POST invalid data → returns 200 with form errors (no redirect)."""
        data = {
            "first_name": "",
            "last_name": "",
            "email": "not-an-email",
            "rol": "estudiante",
            "password1": "short",
            "password2": "different",
        }

        response = self.client.post(self.url, data)

        assert response.status_code == 200
        assert "usuarios/registro.html" in [t.name for t in response.templates]
        # Should NOT create any user
        assert Usuario.objects.count() == 0


# =============================================================================
# TestVerificacionOTPView — 4 tests
# =============================================================================


@pytest.mark.django_db
class TestVerificacionOTPView:
    """View tests for OTP verification (HU01)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:verificar_otp")

    def test_get_sin_session_redirect(self):
        """GET without otp_user_id in session → redirects to registro."""
        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == reverse("usuarios:registro")

    def test_get_con_session(self):
        """GET with otp_user_id in session → returns 200."""
        # Create inactive user
        user = Usuario.objects.create_user(
            username="otp_user",
            email="otp@test.com",
            password=PASSWORD,
            rol="estudiante",
            is_active=False,
        )

        # Put otp_user_id in session
        session = self.client.session
        session["otp_user_id"] = user.pk
        session.save()

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/verificar_otp.html" in [t.name for t in response.templates]

    def test_post_verificacion_exitosa(self):
        """POST correct OTP code → user activated, redirects to login."""
        # Create inactive user + OTP token
        user = Usuario.objects.create_user(
            username="otp_user",
            email="otp@test.com",
            password=PASSWORD,
            rol="estudiante",
            is_active=False,
        )
        codigo = "123456"
        OTPToken.objects.create(
            usuario=user,
            codigo=codigo,
            expira_en=timezone.now() + timedelta(minutes=10),
            usado=False,
        )

        # Put otp_user_id in session
        session = self.client.session
        session["otp_user_id"] = user.pk
        session.save()

        response = self.client.post(self.url, {"codigo": codigo})

        # Redirects to login
        assert response.status_code == 302
        assert response.url == reverse("usuarios:login")

        # User is now active
        user.refresh_from_db()
        assert user.is_active is True

        # OTP token marked as used
        otp = OTPToken.objects.get(usuario=user, codigo=codigo)
        assert otp.usado is True

        # Session otp_user_id cleaned up
        session = self.client.session
        assert "otp_user_id" not in session

    def test_post_codigo_incorrecto(self):
        """POST wrong OTP code → stays on page with error."""
        user = Usuario.objects.create_user(
            username="otp_user",
            email="otp@test.com",
            password=PASSWORD,
            rol="estudiante",
            is_active=False,
        )
        OTPToken.objects.create(
            usuario=user,
            codigo="123456",
            expira_en=timezone.now() + timedelta(minutes=10),
            usado=False,
        )

        session = self.client.session
        session["otp_user_id"] = user.pk
        session.save()

        response = self.client.post(self.url, {"codigo": "000000"})

        # Stays on verification page (re-rendered with error)
        assert response.status_code == 200
        assert "usuarios/verificar_otp.html" in [t.name for t in response.templates]

        # User still inactive
        user.refresh_from_db()
        assert user.is_active is False


# =============================================================================
# TestLoginView — 4 tests
# =============================================================================


@pytest.mark.django_db
class TestLoginView:
    """View tests for login (HU02)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:login")

    def test_get_login_page(self):
        """GET /usuarios/login/ returns 200."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/login.html" in [t.name for t in response.templates]

    def test_get_login_authenticated_redirect(self):
        """GET when already logged in → redirects to dashboard."""
        user = _create_active_user("logged@test.com", rol="inspector")
        self.client.login(username="logged@test.com", password=PASSWORD)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == reverse("usuarios:dashboard")

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_post_login_exitoso(self, mock_lockout):
        """POST valid credentials → redirects to dashboard, user is authenticated."""
        user = _create_active_user("login@test.com", rol="docente")

        data = {
            "email": "login@test.com",
            "password": PASSWORD,
            "tipo_usuario": "docente",
        }

        response = self.client.post(self.url, data)

        # Redirects to dashboard
        assert response.status_code == 302
        assert response.url == reverse("usuarios:dashboard")

        # User is authenticated in session
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.pk == user.pk

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_post_login_credenciales_invalidas(self, mock_lockout):
        """POST wrong password → returns 200 with error message."""
        _create_active_user("login@test.com", rol="inspector")

        data = {
            "email": "login@test.com",
            "password": "WrongPassword!",
            "tipo_usuario": "inspector",
        }

        response = self.client.post(self.url, data)

        # Re-renders login page (no redirect)
        assert response.status_code == 200
        assert "usuarios/login.html" in [t.name for t in response.templates]

        # User is NOT authenticated
        assert not response.wsgi_request.user.is_authenticated


# =============================================================================
# TestLogoutView — 1 test
# =============================================================================


@pytest.mark.django_db
class TestLogoutView:
    """View test for logout (HU02)."""

    def setup_method(self):
        self.client = Client()

    def test_logout(self):
        """GET /usuarios/logout/ → redirects to login, user no longer authenticated."""
        user = _create_active_user("logout@test.com", rol="estudiante")
        self.client.login(username="logout@test.com", password=PASSWORD)

        url = reverse("usuarios:logout")
        response = self.client.get(url)

        # Redirects to login
        assert response.status_code == 302
        assert response.url == reverse("usuarios:login")

        # User no longer authenticated (follow-up request)
        response_after = self.client.get(reverse("usuarios:login"))
        assert not response_after.wsgi_request.user.is_authenticated


# =============================================================================
# TestDashboardRedirectView — 4 tests
# =============================================================================


@pytest.mark.django_db
class TestDashboardRedirectView:
    """View tests for role-based dashboard redirect."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:dashboard")

    def test_dashboard_inspector_redirect(self):
        """Inspector → /academico/periodos/."""
        user = _create_active_user("insp@test.com", rol="inspector")
        self.client.login(username="insp@test.com", password=PASSWORD)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == "/academico/periodos/"

    def test_dashboard_docente_redirect(self):
        """Docente → /academico/paralelos/."""
        user = _create_active_user("doc@test.com", rol="docente")
        self.client.login(username="doc@test.com", password=PASSWORD)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == "/academico/paralelos/"

    def test_dashboard_estudiante_redirect(self):
        """Estudiante → /."""
        user = _create_active_user("est@test.com", rol="estudiante")
        self.client.login(username="est@test.com", password=PASSWORD)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == "/"

    def test_dashboard_anonymous_redirect(self):
        """Anonymous user → login page."""
        response = self.client.get(self.url)

        assert response.status_code == 302
        # login_required redirects to LOGIN_URL with ?next= param
        assert "/usuarios/login/" in response.url


# =============================================================================
# TestPerfilView — 3 tests
# =============================================================================


@pytest.mark.django_db
class TestPerfilView:
    """View tests for profile management (HU04)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:perfil")
        self.user = _create_active_user(
            "perfil@test.com",
            rol="docente",
            first_name="Maria",
            last_name="Garcia",
            telefono="0991111111",
            direccion="Guayaquil",
        )
        self.client.login(username="perfil@test.com", password=PASSWORD)

    def test_get_perfil(self):
        """GET returns 200 with user data in form."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/perfil.html" in [t.name for t in response.templates]

        # Form should contain the user's current data
        content = response.content.decode()
        assert "Maria" in content
        assert "Garcia" in content

    def test_post_actualizar_datos(self):
        """POST → updates user data in DB, redirects to perfil."""
        data = {
            "first_name": "Maria Jose",
            "last_name": "Garcia Torres",
            "telefono": "0999999999",
            "direccion": "Cuenca, Ecuador",
        }

        response = self.client.post(self.url, data)

        # Redirects back to perfil
        assert response.status_code == 302
        assert response.url == reverse("usuarios:perfil")

        # DB updated
        self.user.refresh_from_db()
        assert self.user.first_name == "Maria Jose"
        assert self.user.last_name == "Garcia Torres"
        assert self.user.telefono == "0999999999"
        assert self.user.direccion == "Cuenca, Ecuador"

    def test_perfil_anonymous_redirect(self):
        """Anonymous user → redirects to login."""
        anonymous_client = Client()

        response = anonymous_client.get(self.url)

        assert response.status_code == 302
        assert "/usuarios/login/" in response.url


# =============================================================================
# TestCambiarContrasenaView — 2 tests
# =============================================================================


@pytest.mark.django_db
class TestCambiarContrasenaView:
    """View tests for password change (HU04)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:cambiar_contrasena")
        self.user = _create_active_user("cambio@test.com", rol="estudiante")
        self.client.login(username="cambio@test.com", password=PASSWORD)

    def test_cambiar_contrasena_exitoso(self):
        """POST old + new → password changed, redirects to perfil."""
        new_password = "NewSecure456!"
        data = {
            "old_password": PASSWORD,
            "new_password1": new_password,
            "new_password2": new_password,
        }

        response = self.client.post(self.url, data)

        # Redirects to perfil
        assert response.status_code == 302
        assert response.url == reverse("usuarios:perfil")

        # Password actually changed in DB
        self.user.refresh_from_db()
        assert self.user.check_password(new_password) is True
        assert self.user.check_password(PASSWORD) is False

    def test_cambiar_contrasena_password_incorrecto(self):
        """POST wrong old password → stays on page with error."""
        data = {
            "old_password": "WrongOldPass!",
            "new_password1": "NewSecure456!",
            "new_password2": "NewSecure456!",
        }

        response = self.client.post(self.url, data)

        # Re-renders change password page (no redirect)
        assert response.status_code == 200
        assert "usuarios/cambiar_contrasena.html" in [
            t.name for t in response.templates
        ]

        # Password unchanged
        self.user.refresh_from_db()
        assert self.user.check_password(PASSWORD) is True


# =============================================================================
# TestPasswordRecovery — 1 test
# =============================================================================


@pytest.mark.django_db
class TestPasswordRecovery:
    """View test for password recovery page (HU03)."""

    def setup_method(self):
        self.client = Client()

    def test_get_password_reset_page(self):
        """GET /usuarios/recuperar/ returns 200 with correct template."""
        url = reverse("usuarios:password_reset")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "registration/password_reset_form.html" in [
            t.name for t in response.templates
        ]
