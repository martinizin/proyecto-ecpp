"""Tests for Secretaría templates — a11y contracts and UX copy."""

import pytest
from django.urls import reverse

from tests.factories import SecretariaFactory

pytestmark = pytest.mark.django_db


def _make_sec():
    user = SecretariaFactory()
    user.save()
    return user


class TestConfirmCreateModal:
    """A11y and content contract for confirm_create_modal.html partial."""

    def setup_method(self):
        self.url = reverse("secretaria:usuario_create")

    def _get_html(self, client):
        sec = _make_sec()
        client.force_login(sec)
        response = client.get(self.url)
        assert response.status_code == 200
        return response.content.decode()

    def test_confirm_create_modal_tiene_role_dialog(self, client):
        """Modal root element must carry role="dialog"."""
        html = self._get_html(client)
        assert 'role="dialog"' in html

    def test_confirm_create_modal_tiene_aria_modal(self, client):
        """Modal must declare aria-modal="true"."""
        html = self._get_html(client)
        assert 'aria-modal="true"' in html

    def test_confirm_create_modal_tiene_aria_labelledby(self, client):
        """Modal must link its label via aria-labelledby='modal-titulo-crear'."""
        html = self._get_html(client)
        assert 'aria-labelledby="modal-titulo-crear"' in html

    def test_confirm_create_modal_tiene_keydown_escape(self, client):
        """ESC key must close the modal (@keydown.escape.window binding)."""
        html = self._get_html(client)
        assert "@keydown.escape.window" in html

    def test_confirm_create_modal_tiene_click_backdrop(self, client):
        """Clicking the backdrop must close the modal (@click.self binding)."""
        html = self._get_html(client)
        assert "@click.self" in html

    def test_confirm_create_modal_botones_revisar_y_crear(self, client):
        """Modal must have 'Revisar' and 'Crear usuario' buttons."""
        html = self._get_html(client)
        assert "Revisar" in html
        assert "Crear usuario" in html


class TestUsuarioFormAdvertencia:
    """Immutability warning copy in usuario_form.html."""

    def setup_method(self):
        self.url = reverse("secretaria:usuario_create")

    def test_usuario_form_muestra_advertencia_cedula_inmutable(self, client):
        """Form page must display immutability warning text."""
        sec = _make_sec()
        client.force_login(sec)
        response = client.get(self.url)
        assert response.status_code == 200
        html = response.content.decode()
        assert "no podr" in html  # "no podrá modificarse"
