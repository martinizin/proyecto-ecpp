"""
Tests for notification API views.
"""

import pytest
from django.test import Client

from tests.factories import NotificacionFactory, UsuarioFactory


def _saved(user):
    """Persist password hash so force_login session survives request cycle."""
    user.save()
    return user


@pytest.mark.django_db
class TestContadorNoLeidas:
    def test_contador_no_leidas(self):
        user = _saved(UsuarioFactory())
        NotificacionFactory(destinatario=user, leida=False)
        NotificacionFactory(destinatario=user, leida=False)
        NotificacionFactory(destinatario=user, leida=True)

        client = Client()
        client.force_login(user)
        resp = client.get("/notificaciones/contador/")
        assert resp.status_code == 200
        assert resp.json()["no_leidas"] == 2


@pytest.mark.django_db
class TestListaNotificaciones:
    def test_lista_notificaciones(self):
        user = _saved(UsuarioFactory())
        other = _saved(UsuarioFactory())
        NotificacionFactory(destinatario=user, titulo="Mía")
        NotificacionFactory(destinatario=other, titulo="Ajena")

        client = Client()
        client.force_login(user)
        resp = client.get("/notificaciones/")
        data = resp.json()

        assert resp.status_code == 200
        assert len(data["notificaciones"]) == 1
        assert data["notificaciones"][0]["titulo"] == "Mía"

    def test_lista_vacia(self):
        user = _saved(UsuarioFactory())
        client = Client()
        client.force_login(user)
        resp = client.get("/notificaciones/")
        data = resp.json()

        assert data["notificaciones"] == []
        assert data["no_leidas"] == 0


@pytest.mark.django_db
class TestMarcarLeida:
    def test_marcar_leida(self):
        user = _saved(UsuarioFactory())
        notif = NotificacionFactory(destinatario=user, leida=False)

        client = Client()
        client.force_login(user)
        resp = client.post(f"/notificaciones/{notif.pk}/leer/")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        notif.refresh_from_db()
        assert notif.leida is True

    def test_marcar_leida_otro_usuario(self):
        user = _saved(UsuarioFactory())
        other = _saved(UsuarioFactory())
        notif = NotificacionFactory(destinatario=other)

        client = Client()
        client.force_login(user)
        resp = client.post(f"/notificaciones/{notif.pk}/leer/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestMarcarTodasLeidas:
    def test_marcar_todas_leidas(self):
        user = _saved(UsuarioFactory())
        NotificacionFactory(destinatario=user, leida=False)
        NotificacionFactory(destinatario=user, leida=False)
        NotificacionFactory(destinatario=user, leida=True)

        client = Client()
        client.force_login(user)
        resp = client.post("/notificaciones/leer-todas/")
        data = resp.json()

        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["actualizadas"] == 2


@pytest.mark.django_db
class TestLoginRequired:
    def test_login_required(self):
        client = Client()
        resp = client.get("/notificaciones/contador/")
        assert resp.status_code == 302
