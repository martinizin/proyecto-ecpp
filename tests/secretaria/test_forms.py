"""Tests for Secretaría forms."""

import pytest

from apps.secretaria.forms import CrearUsuarioForm

pytestmark = pytest.mark.django_db


class TestCrearUsuarioForm:
    """Tests for CrearUsuarioForm."""

    VALID_DATA = {
        "email": "nuevo@test.com",
        "first_name": "Juan",
        "last_name": "Perez",
        "rol": "estudiante",
        "cedula": "1710034065",
    }

    def test_crear_usuario_form_cedula_required(self):
        """Submitting without cedula → form invalid with 'cedula' error key."""
        data = {**self.VALID_DATA, "cedula": ""}
        form = CrearUsuarioForm(data=data)
        assert not form.is_valid()
        assert "cedula" in form.errors

    def test_crear_usuario_form_valid_data(self):
        """Valid data passes form validation."""
        form = CrearUsuarioForm(data=self.VALID_DATA)
        assert form.is_valid(), form.errors

    def test_no_editar_usuario_form_symbol(self):
        """EditarUsuarioForm must not be importable from forms module."""
        import apps.secretaria.forms as forms_module

        assert not hasattr(forms_module, "EditarUsuarioForm")
