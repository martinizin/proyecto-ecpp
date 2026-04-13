"""
View tests for the Usuarios bounded context using Django test Client.

Tests: LoginView (direct + 2FA), Verificacion2FAView, LogoutView,
       DashboardRedirectView, PerfilView, CambiarContrasenaView,
       PasswordRecovery, ForzarCambioPasswordMiddleware, UsuarioAdmin.
Refs: HU01→HU04, SCN-AUTH-01→10, SCN-PROF-01→08

NOTE: Public registration was removed — users are created by staff via Django Admin.
      TestRegistroView and TestVerificacionOTPView were removed accordingly.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.admin import UsuarioAdmin, UsuarioCreationForm
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
# TestLoginView — 5 tests (4 original + 1 new for 2FA redirect)
# =============================================================================


@pytest.mark.django_db
class TestLoginView:
    """View tests for login (HU02) — includes 2FA redirect for students."""

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
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == reverse("usuarios:dashboard")

    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_post_login_exitoso_docente(self, mock_lockout):
        """POST valid credentials (docente) → direct login, redirects to dashboard."""
        user = _create_active_user("login@test.com", rol="docente")

        data = {
            "email": "login@test.com",
            "password": PASSWORD,
            "tipo_usuario": "docente",
        }

        response = self.client.post(self.url, data)

        # Redirects to dashboard (direct login, no 2FA)
        assert response.status_code == 302
        assert response.url == reverse("usuarios:dashboard")

        # User is authenticated in session
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.pk == user.pk

    @patch("apps.usuarios.application.services.send_otp_email")
    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_post_login_estudiante_redirige_a_2fa(self, mock_lockout, mock_otp):
        """POST valid credentials (estudiante) → redirects to verificar_2fa, NOT dashboard."""
        _create_active_user("estudiante@test.com", rol="estudiante")

        data = {
            "email": "estudiante@test.com",
            "password": PASSWORD,
            "tipo_usuario": "estudiante",
        }

        response = self.client.post(self.url, data)

        # Redirects to 2FA verification (NOT to dashboard)
        assert response.status_code == 302
        assert response.url == reverse("usuarios:verificar_2fa")

        # User is NOT authenticated yet (login happens after OTP)
        assert not response.wsgi_request.user.is_authenticated

        # Session contains 2fa_user_id
        assert "2fa_user_id" in self.client.session

        # OTP email was sent
        mock_otp.assert_called_once()

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
# TestVerificacion2FAView — 4 tests
# =============================================================================


@pytest.mark.django_db
class TestVerificacion2FAView:
    """View tests for 2FA OTP verification — student login flow (HU02)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:verificar_2fa")

    def test_get_sin_session_redirect(self):
        """GET without 2fa_user_id in session → redirects to login."""
        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == reverse("usuarios:login")

    def test_get_con_session(self):
        """GET with 2fa_user_id in session → returns 200."""
        user = _create_active_user("est2fa@test.com", rol="estudiante")

        # Put 2fa_user_id in session
        session = self.client.session
        session["2fa_user_id"] = user.pk
        session.save()

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/verificar_2fa.html" in [t.name for t in response.templates]

    def test_post_verificacion_exitosa(self):
        """POST correct OTP → user logged in, redirects to dashboard."""
        user = _create_active_user("est2fa@test.com", rol="estudiante")
        codigo = "123456"
        OTPToken.objects.create(
            usuario=user,
            codigo=codigo,
            expira_en=timezone.now() + timedelta(minutes=10),
            usado=False,
        )

        # Put 2fa_user_id in session
        session = self.client.session
        session["2fa_user_id"] = user.pk
        session.save()

        response = self.client.post(self.url, {"codigo": codigo})

        # Redirects to dashboard
        assert response.status_code == 302
        assert response.url == reverse("usuarios:dashboard")

        # User is now authenticated
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.pk == user.pk

        # OTP token marked as used
        otp = OTPToken.objects.get(usuario=user, codigo=codigo)
        assert otp.usado is True

        # 2fa_user_id cleaned from session
        assert "2fa_user_id" not in self.client.session

    def test_post_codigo_incorrecto(self):
        """POST wrong OTP code → stays on page with error."""
        user = _create_active_user("est2fa@test.com", rol="estudiante")
        OTPToken.objects.create(
            usuario=user,
            codigo="123456",
            expira_en=timezone.now() + timedelta(minutes=10),
            usado=False,
        )

        session = self.client.session
        session["2fa_user_id"] = user.pk
        session.save()

        response = self.client.post(self.url, {"codigo": "000000"})

        # Stays on 2FA page (re-rendered with error)
        assert response.status_code == 200
        assert "usuarios/verificar_2fa.html" in [t.name for t in response.templates]

        # User NOT authenticated
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
        self.client.force_login(user)

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
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == "/academico/periodos/"

    def test_dashboard_docente_redirect(self):
        """Docente → /academico/paralelos/."""
        user = _create_active_user("doc@test.com", rol="docente")
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 302
        assert response.url == "/academico/paralelos/"

    def test_dashboard_estudiante_redirect(self):
        """Estudiante → /."""
        user = _create_active_user("est@test.com", rol="estudiante")
        self.client.force_login(user)

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
        self.client.force_login(self.user)

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
# TestCambiarContrasenaView — 3 tests (2 original + 1 new for debe_cambiar_password)
# =============================================================================


@pytest.mark.django_db
class TestCambiarContrasenaView:
    """View tests for password change (HU04)."""

    def setup_method(self):
        self.client = Client()
        self.url = reverse("usuarios:cambiar_contrasena")
        self.user = _create_active_user("cambio@test.com", rol="estudiante")
        self.client.force_login(self.user)

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

    def test_cambiar_contrasena_limpia_debe_cambiar_password(self):
        """POST with debe_cambiar_password=True → flag cleared after password change."""
        # Set the temporary password flag
        self.user.debe_cambiar_password = True
        self.user.save(update_fields=["debe_cambiar_password"])

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

        # Flag cleared
        self.user.refresh_from_db()
        assert self.user.debe_cambiar_password is False
        assert self.user.check_password(new_password) is True


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


# =============================================================================
# TestForzarCambioPasswordMiddleware — 3 tests
# =============================================================================


@pytest.mark.django_db
class TestForzarCambioPasswordMiddleware:
    """Tests for the middleware that forces password change on temporary passwords."""

    def setup_method(self):
        self.client = Client()

    def test_redirige_cuando_debe_cambiar_password(self):
        """Authenticated user with debe_cambiar_password=True → redirects to cambiar_contrasena."""
        user = _create_active_user("temp@test.com", rol="docente")
        user.debe_cambiar_password = True
        user.save(update_fields=["debe_cambiar_password"])
        self.client.force_login(user)

        # Try to access dashboard
        response = self.client.get(reverse("usuarios:dashboard"))

        # Should redirect to password change page (not follow the dashboard redirect)
        assert response.status_code == 302
        assert response.url == reverse("usuarios:cambiar_contrasena")

    def test_permite_acceso_cambiar_contrasena(self):
        """User with debe_cambiar_password=True CAN access the password change page."""
        user = _create_active_user("temp@test.com", rol="docente")
        user.debe_cambiar_password = True
        user.save(update_fields=["debe_cambiar_password"])
        self.client.force_login(user)

        response = self.client.get(reverse("usuarios:cambiar_contrasena"))

        # Should return 200 (not redirect — the page itself is exempt)
        assert response.status_code == 200
        assert "usuarios/cambiar_contrasena.html" in [t.name for t in response.templates]

    def test_no_redirige_cuando_no_debe_cambiar(self):
        """Authenticated user with debe_cambiar_password=False → normal flow."""
        user = _create_active_user("normal@test.com", rol="inspector")
        assert user.debe_cambiar_password is False
        self.client.force_login(user)

        response = self.client.get(reverse("usuarios:perfil"))

        # Should access perfil normally (no redirect to password change)
        assert response.status_code == 200
        assert "usuarios/perfil.html" in [t.name for t in response.templates]


# =============================================================================
# TestUsuarioAdmin — 3 tests
# =============================================================================


@pytest.mark.django_db
class TestUsuarioAdmin:
    """Tests for the customized UsuarioAdmin — user creation by secretariat."""

    def setup_method(self):
        self.site = AdminSite()
        self.admin = UsuarioAdmin(Usuario, self.site)
        self.factory = RequestFactory()

    @patch("apps.usuarios.admin.send_credenciales_email")
    def test_creacion_genera_password_temporal(self, mock_send_email):
        """save_model on new user → generates temp password, sets debe_cambiar_password=True."""
        # Create superuser for admin request
        superuser = _create_active_user(
            "admin@test.com", rol="inspector", is_staff=True, is_superuser=True
        )

        request = self.factory.post("/admin/usuarios/usuario/add/")
        request.user = superuser
        # Django messages framework needs session middleware
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))

        # Create user object (simulating form save)
        user = Usuario(
            email="nuevo@test.com",
            first_name="Nuevo",
            last_name="Usuario",
            rol="estudiante",
            cedula="1710034065",
        )

        form = UsuarioCreationForm(
            data={
                "email": "nuevo@test.com",
                "first_name": "Nuevo",
                "last_name": "Usuario",
                "rol": "estudiante",
                "cedula": "1710034065",
                "telefono": "0991234567",
            }
        )
        form.is_valid()

        # change=False → new user creation
        self.admin.save_model(request, user, form, change=False)

        # User was saved with correct properties
        saved_user = Usuario.objects.get(email="nuevo@test.com")
        assert saved_user.is_active is True
        assert saved_user.debe_cambiar_password is True
        assert saved_user.username == "nuevo@test.com"
        assert saved_user.has_usable_password() is True

        # Email was sent with credentials
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args[0][0].email == "nuevo@test.com"
        # Second arg is the temp password (a string of length 12)
        temp_password = call_args[0][1]
        assert len(temp_password) == 12

    @patch("apps.usuarios.admin.send_credenciales_email")
    def test_creacion_email_falla_muestra_password(self, mock_send_email):
        """save_model when email fails → shows temp password in admin warning."""
        mock_send_email.side_effect = Exception("SMTP error")

        superuser = _create_active_user(
            "admin@test.com", rol="inspector", is_staff=True, is_superuser=True
        )

        request = self.factory.post("/admin/usuarios/usuario/add/")
        request.user = superuser
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))

        user = Usuario(
            email="fallo@test.com",
            first_name="Fallo",
            last_name="Email",
            rol="docente",
        )

        form = UsuarioCreationForm(
            data={
                "email": "fallo@test.com",
                "first_name": "Fallo",
                "last_name": "Email",
                "rol": "docente",
                "cedula": "",
                "telefono": "",
            }
        )
        form.is_valid()

        self.admin.save_model(request, user, form, change=False)

        # User was still created despite email failure
        saved_user = Usuario.objects.get(email="fallo@test.com")
        assert saved_user.is_active is True
        assert saved_user.debe_cambiar_password is True

        # Check that warning message was added (containing the temp password)
        stored_messages = [m.message for m in request._messages]
        assert any("Contraseña temporal:" in msg for msg in stored_messages)

    def test_creation_form_valida_email_duplicado(self):
        """UsuarioCreationForm rejects duplicate email."""
        _create_active_user("existe@test.com", rol="estudiante")

        form = UsuarioCreationForm(
            data={
                "email": "existe@test.com",
                "first_name": "Duplicado",
                "last_name": "Test",
                "rol": "estudiante",
                "cedula": "1710034065",
                "telefono": "",
            }
        )

        assert form.is_valid() is False
        assert "email" in form.errors
