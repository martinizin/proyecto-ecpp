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
import json
import time
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
    """View tests for login (HU02) — includes 2FA redirect for all roles."""

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

    @patch("apps.usuarios.application.services.send_otp_email")
    @patch("apps.usuarios.application.services.send_lockout_notification")
    def test_post_login_exitoso_docente_redirige_a_2fa(self, mock_lockout, mock_otp):
        """POST valid credentials (docente) → redirects to 2FA verification."""
        _create_active_user("login@test.com", rol="docente")

        data = {
            "email": "login@test.com",
            "password": PASSWORD,
            "tipo_usuario": "docente",
        }

        response = self.client.post(self.url, data)

        assert response.status_code == 302
        assert response.url == reverse("usuarios:verificar_2fa")
        mock_otp.assert_called_once()

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

    def test_dashboard_inspector_renders(self):
        """Inspector → renders dashboard template."""
        user = _create_active_user("insp@test.com", rol="inspector")
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/dashboard.html" in [t.name for t in response.templates]

    def test_dashboard_docente_renders(self):
        """Docente → renders dashboard template."""
        user = _create_active_user("doc@test.com", rol="docente")
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/dashboard.html" in [t.name for t in response.templates]

    def test_dashboard_estudiante_redirect(self):
        """Estudiante → renders dashboard template."""
        user = _create_active_user("est@test.com", rol="estudiante")
        self.client.force_login(user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert "usuarios/dashboard.html" in [t.name for t in response.templates]

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
        assert "usuarios/cambiar_contrasena.html" in [t.name for t in response.templates]

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
        assert "registration/password_reset_form.html" in [t.name for t in response.templates]


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
            "admin@test.com",
            rol="inspector",
            is_staff=True,
            is_superuser=True,
            cedula="1710034065",
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
            cedula="0926687856",
        )

        form = UsuarioCreationForm(
            data={
                "email": "fallo@test.com",
                "first_name": "Fallo",
                "last_name": "Email",
                "rol": "docente",
                "cedula": "0926687856",
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


# =============================================================================
# TestSessionTimeoutMiddleware — HU31 (3 tests in WU1; T4 + T5 added later)
# =============================================================================


@pytest.mark.django_db
class TestSessionTimeoutMiddleware:
    """Tests for the middleware that closes the session on idle (HU31)."""

    def setup_method(self):
        self.client = Client()

    def test_actualiza_last_activity_en_request_autenticado(self):
        # T1: usuario fresco → la middleware escribe last_activity, no redirige
        user = _create_active_user("active@test.com", rol="docente")
        self.client.force_login(user)

        before = int(time.time())
        response = self.client.get(reverse("usuarios:perfil"))
        after = int(time.time())

        assert response.status_code == 200
        assert before <= int(self.client.session["last_activity"]) <= after

    def test_redirige_a_login_expired_si_inactivo_mas_de_timeout(self):
        # T2: idle > 20 min → 302 a login?session=expired, sesión flusheada
        user = _create_active_user("idle@test.com", rol="docente")
        self.client.force_login(user)
        session = self.client.session
        session["last_activity"] = time.time() - 1201
        session.save()

        response = self.client.get(reverse("usuarios:perfil"))

        assert response.status_code == 302
        assert response.url == reverse("usuarios:login") + "?session=expired"
        # session is flushed — anonymous on the next request
        assert "_auth_user_id" not in self.client.session

    def test_no_hace_nada_para_usuario_anonimo(self):
        # T3: anónimo → la middleware es no-op (no redirige, no escribe last_activity)
        response = self.client.get(reverse("usuarios:login"))

        assert response.status_code == 200
        assert "last_activity" not in self.client.session

    def test_exempt_path_no_redirige(self):
        # T4: hitting /api/session/extend/ while expired must NOT log the user out
        user = _create_active_user("exempt@test.com", rol="docente")
        self.client.force_login(user)
        session = self.client.session
        session["last_activity"] = time.time() - 1500  # deep in expired zone
        session.save()

        response = self.client.post(reverse("usuarios:session_extend"))

        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ok"}
        # last_activity was rewritten by the endpoint
        assert self.client.session["last_activity"] >= time.time() - 1

    def test_no_redirige_usuario_con_debe_cambiar_password(self):
        # T5: ordering — ForzarCambioPassword runs first, user goes to cambiar_contrasena
        # Invarint: aunque la sesión esté vencida (>1200s idle), un usuario con
        # debe_cambiar_password=True debe terminar en cambiar_contrasena, no en
        # login?session=expired. Verifica R2.4 y la locked decision #2.
        user = _create_active_user("temp@test.com", rol="docente")
        user.debe_cambiar_password = True
        user.save(update_fields=["debe_cambiar_password"])
        self.client.force_login(user)
        session = self.client.session
        session["last_activity"] = time.time() - 1500  # also expired
        session.save()

        response = self.client.get(reverse("usuarios:perfil"))

        assert response.status_code == 302
        assert response.url == reverse("usuarios:cambiar_contrasena")
        # NOT the login-expired URL — password-change wins
        assert "session=expired" not in response.url

    def test_throttle_no_escribe_si_request_dentro_de_60s(self):
        # T14: si la última escritura de ``last_activity`` fue hace menos
        # de ``SESSION_UPDATE_INTERVAL_SECONDS`` (default 60s), el
        # siguiente request NO triggerea UPDATE de ``django_session``.
        # Verifica la producción: ráfagas de requests no generan N writes.
        # Para testear esto, ``request.session.modified`` debe ser False
        # al salir del middleware — no podemos observar eso directamente
        # desde el test, pero SÍ podemos observar que el valor de
        # ``last_activity`` no cambió después de un request dentro del
        # window de throttle.
        user = _create_active_user("throttle-fresh@test.com", rol="docente")
        self.client.force_login(user)
        # Setear ``last_activity`` a un valor MUY reciente (10s atrás).
        # Cualquier cosa <60s debería skip el write.
        recent = int(time.time()) - 10
        session = self.client.session
        session["last_activity"] = recent
        session.save()

        self.client.get(reverse("usuarios:perfil"))

        # Después de un request dentro del window de throttle, el valor
        # de ``last_activity`` no debe haber sido actualizado. Esto
        # verifica indirectamente que la middleware NO escribió en la
        # sesión.
        session = self.client.session
        assert int(session["last_activity"]) == recent

    def test_throttle_escribe_despues_de_60s(self):
        # T15: si la última escritura fue hace MÁS de
        # ``SESSION_UPDATE_INTERVAL_SECONDS`` (default 60s), el siguiente
        # request SÍ triggerea UPDATE con el valor actualizado.
        # Complemento de T14.
        user = _create_active_user("throttle-stale@test.com", rol="docente")
        self.client.force_login(user)
        # Setear ``last_activity`` a 90s atrás (mayor al default 60s).
        stale = int(time.time()) - 90
        session = self.client.session
        session["last_activity"] = stale
        session.save()

        before = int(time.time())
        self.client.get(reverse("usuarios:perfil"))
        after = int(time.time())

        # Después de un request fuera del window de throttle, el valor
        # de ``last_activity`` debe haber sido actualizado a now (entre
        # ``before`` y ``after``).
        session = self.client.session
        assert before <= int(session["last_activity"]) <= after
        assert int(session["last_activity"]) > stale


# =============================================================================
# TestSessionEndpoints — HU31 (6 tests: T6, T7, T8, T9, T10, T11)
# =============================================================================


@pytest.mark.django_db
class TestSessionEndpoints:
    """Tests para los 3 endpoints JSON bajo /api/session/ (HU31)."""

    def setup_method(self):
        self.client = Client()

    def _login_fresh(self, email: str = "ep@test.com") -> None:
        user = _create_active_user(email, rol="docente")
        self.client.force_login(user)

    def test_check_retorna_warning_false_si_fresco(self):
        # T6: fresh → warning=False, expired=False, remaining ≈ 1200
        self._login_fresh()

        response = self.client.get(reverse("usuarios:session_check"))

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body == {"warning": False, "expired": False, "remaining": 1200}

    def test_check_retorna_warning_true_si_en_zona_warning(self):
        # T7: 18:20 idle (1100s) → warning=True, expired=False, remaining=100
        self._login_fresh("warn@test.com")
        session = self.client.session
        session["last_activity"] = time.time() - 1100
        session.save()

        response = self.client.get(reverse("usuarios:session_check"))

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["warning"] is True
        assert body["expired"] is False
        assert 95 <= body["remaining"] <= 105  # tolerance for test execution

    def test_check_retorna_expired_true_si_pasado_timeout(self):
        # T8: server-side: 1201s idle → middleware flushes BEFORE the view runs
        # → @login_required returns 302 to login. The client treats 302
        # as "expired" and redirects to logout (see design.md §5.4).
        self._login_fresh("exp@test.com")
        session = self.client.session
        session["last_activity"] = time.time() - 1201
        session.save()

        response = self.client.get(reverse("usuarios:session_check"))

        assert response.status_code == 302
        assert response.url == reverse("usuarios:login") + "?session=expired"

    def test_extend_actualiza_last_activity(self):
        # T9: POST /api/session/extend/ → 200, last_activity reset
        self._login_fresh("ext@test.com")
        session = self.client.session
        session["last_activity"] = time.time() - 600
        session.save()

        response = self.client.post(reverse("usuarios:session_extend"))

        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ok"}
        assert self.client.session["last_activity"] >= time.time() - 1

    def test_touch_actualiza_last_activity(self):
        # T10: POST /api/session/touch/ → 200, last_activity reset
        self._login_fresh("touch@test.com")
        session = self.client.session
        session["last_activity"] = time.time() - 600
        session.save()

        response = self.client.post(reverse("usuarios:session_touch"))

        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ok"}
        assert self.client.session["last_activity"] >= time.time() - 1

    def test_endpoints_requieren_login(self):
        # T11: anonymous calls to all 3 endpoints → 302 to login
        for url_name, method in [
            ("usuarios:session_check", "get"),
            ("usuarios:session_extend", "post"),
            ("usuarios:session_touch", "post"),
        ]:
            response = getattr(self.client, method)(reverse(url_name))
            assert (
                response.status_code == 302
            ), f"{url_name} {method} expected 302, got {response.status_code}"
            assert reverse("usuarios:login") in response.url


# =============================================================================
# TestLoginExpiredBanner — HU31 (1 test: T12)
# =============================================================================


@pytest.mark.django_db
class TestLoginExpiredBanner:
    """Tests para el banner de sesión expirada en login.html (HU31)."""

    def setup_method(self):
        self.client = Client()

    def test_login_muestra_banner_si_session_expired_query_param(self):
        # T12: GET /usuarios/login/?session=expired → role="alert" + texto
        response = self.client.get(reverse("usuarios:login") + "?session=expired")

        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert 'role="alert"' in body
        assert "Su sesión ha expirado por inactividad" in body

    def test_login_no_muestra_banner_sin_query_param(self):
        # Guard de R9: el banner NO aparece si no viene ?session=expired
        response = self.client.get(reverse("usuarios:login"))

        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert "Su sesión ha expirado por inactividad" not in body
