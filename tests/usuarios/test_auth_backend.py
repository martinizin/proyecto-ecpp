"""
Tests for ECPPPAuthBackend.
Integration tests — require database.
Tests: success, wrong password, wrong tipo_usuario, inactive user, missing fields.
Ref: AC-AUTH-07, AD1
"""

import pytest

from apps.usuarios.infrastructure.auth_backend import ECPPPAuthBackend
from apps.usuarios.infrastructure.models import Usuario


@pytest.fixture
def backend():
    return ECPPPAuthBackend()


@pytest.fixture
def active_user(db):
    """Create an active user for auth tests."""
    return Usuario.objects.create_user(
        username="auth_test",
        email="auth@test.com",
        password="TestPass123!",
        rol=Usuario.Rol.INSPECTOR,
        is_active=True,
    )


@pytest.fixture
def inactive_user(db):
    """Create an inactive user for auth tests."""
    return Usuario.objects.create_user(
        username="inactive_test",
        email="inactive@test.com",
        password="TestPass123!",
        rol=Usuario.Rol.ESTUDIANTE,
        is_active=False,
    )


class TestECPPPAuthBackend:
    """Tests for triple-field authentication (email + password + tipo_usuario)."""

    def test_authenticate_success(self, backend, active_user):
        """Valid email + password + tipo_usuario should return the user."""
        user = backend.authenticate(
            request=None,
            email="auth@test.com",
            password="TestPass123!",
            tipo_usuario="inspector",
        )
        assert user is not None
        assert user.pk == active_user.pk

    def test_authenticate_success_sin_tipo_usuario(self, backend, active_user):
        """Valid email + password without tipo_usuario should still work."""
        user = backend.authenticate(
            request=None,
            email="auth@test.com",
            password="TestPass123!",
        )
        assert user is not None
        assert user.pk == active_user.pk

    def test_authenticate_wrong_password(self, backend, active_user):
        """Wrong password should return None."""
        user = backend.authenticate(
            request=None,
            email="auth@test.com",
            password="WrongPassword!",
            tipo_usuario="inspector",
        )
        assert user is None

    def test_authenticate_wrong_tipo_usuario(self, backend, active_user):
        """Correct credentials but wrong role should return None."""
        user = backend.authenticate(
            request=None,
            email="auth@test.com",
            password="TestPass123!",
            tipo_usuario="docente",
        )
        assert user is None

    def test_authenticate_inactive_user(self, backend, inactive_user):
        """Inactive user should return None even with correct credentials."""
        user = backend.authenticate(
            request=None,
            email="inactive@test.com",
            password="TestPass123!",
            tipo_usuario="estudiante",
        )
        assert user is None

    def test_authenticate_nonexistent_email(self, backend, active_user):
        """Non-existent email should return None."""
        user = backend.authenticate(
            request=None,
            email="noexiste@test.com",
            password="TestPass123!",
            tipo_usuario="inspector",
        )
        assert user is None

    def test_authenticate_email_none(self, backend):
        """None email should return None."""
        user = backend.authenticate(
            request=None,
            email=None,
            password="TestPass123!",
        )
        assert user is None

    def test_authenticate_password_none(self, backend):
        """None password should return None."""
        user = backend.authenticate(
            request=None,
            email="auth@test.com",
            password=None,
        )
        assert user is None
