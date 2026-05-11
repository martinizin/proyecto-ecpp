"""
Tests for Notificacion model.
"""

import pytest

from tests.factories import NotificacionFactory, UsuarioFactory


@pytest.mark.django_db
class TestNotificacionModel:
    def test_crear_notificacion(self):
        notif = NotificacionFactory()
        assert notif.pk is not None
        assert notif.leida is False
        assert notif.tipo == "general"

    def test_ordering(self):
        user = UsuarioFactory()
        n1 = NotificacionFactory(destinatario=user, titulo="Primera")
        n2 = NotificacionFactory(destinatario=user, titulo="Segunda")

        from apps.notificaciones.infrastructure.models import Notificacion

        qs = list(Notificacion.objects.filter(destinatario=user))
        assert qs[0].pk == n2.pk
        assert qs[1].pk == n1.pk

    def test_str(self):
        notif = NotificacionFactory(titulo="Alerta test")
        assert "Alerta test" in str(notif)
        assert str(notif.destinatario) in str(notif)
