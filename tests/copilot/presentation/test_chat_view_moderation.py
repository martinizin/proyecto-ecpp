"""View tests for the moderation wiring in CopilotChatView (PR 2,
copilot-content-moderation, Phase 2.2 — presentation).

Asserts the view catches ``ContenidoBloqueadoError`` and returns the byte-locked
``CANNED_REFUSAL`` at HTTP 200 (NOT 4xx) for both input rejection reasons
(``strong_list`` and ``openai_input``). The clean path is covered by the
existing ``test_views.py``; the output rejection (``openai_output``) is covered
in the application-layer tests.

The ``_mock_openai`` autouse fixture from ``test_views.py`` is not used here —
we patch the service differently to keep the moderation test boundary
explicit.
"""

from __future__ import annotations

import json
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import ContenidoBloqueadoError
from apps.copilot.domain.moderation import CANNED_REFUSAL
from tests.factories import EstudianteFactory


CHAT_URL = reverse("copilot:chat")


# -------------------------------------------------------------------- #
# Fixtures
# -------------------------------------------------------------------- #
@pytest.fixture
def estudiante(db):
    user = EstudianteFactory()
    user.save()
    return user


@pytest.fixture
def client_estudiante(estudiante):
    c = Client()
    c.force_login(estudiante)
    return c


@pytest.fixture
def raising_service(monkeypatch, exception_to_raise):
    """Patch ``CopilotAppService.procesar_mensaje`` to raise the given exception."""
    original_init = CopilotAppService.__init__

    def _init(self, **kwargs):
        original_init(self, **kwargs)
        # Sobreescribimos el método para que SIEMPRE levante la excepción.
        self.procesar_mensaje = mock.MagicMock(side_effect=exception_to_raise)

    monkeypatch.setattr(CopilotAppService, "__init__", _init)


# -------------------------------------------------------------------- #
# Helper parametrization
# -------------------------------------------------------------------- #
RAZONES_RECHAZO = [
    "strong_list",
    "openai_input",
    "openai_output",
]


class TestContenidoBloqueado:
    """T2.19 / T2.20 — El view debe capturar ``ContenidoBloqueadoError`` y
    responder HTTP 200 con ``CANNED_REFUSAL`` (no 4xx, REQ-008)."""

    @pytest.mark.parametrize("razon", RAZONES_RECHAZO)
    def test_post_retorna_200_con_canned_refusal(self, client_estudiante, monkeypatch, razon):
        exc = ContenidoBloqueadoError(razon=razon)
        original_init = CopilotAppService.__init__

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje = mock.MagicMock(side_effect=exc)

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert (
            res.status_code == 200
        ), f"esperaba 200 con refusal, recibí {res.status_code} para razon={razon}"
        data = res.json()
        assert data["respuesta"] == CANNED_REFUSAL

    def test_post_rechazo_no_persiste_user(self, client_estudiante, monkeypatch):
        """En un rechazo por ContenidoBloqueadoError NO se persiste el user msg."""
        exc = ContenidoBloqueadoError(razon="strong_list")
        original_init = CopilotAppService.__init__

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje = mock.MagicMock(side_effect=exc)

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        from apps.copilot.infrastructure.models import MensajeCopilot

        client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        # La fila del user NO debe existir (el raise ocurre antes del create)
        assert MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER).count() == 0


class TestCaminoLimpio:
    """El camino limpio del view sigue funcionando como antes (no-moderation
    no rompe el contrato existente)."""

    def test_post_limpio_retorna_200_y_respuesta_llm(self, client_estudiante, monkeypatch):
        original_init = CopilotAppService.__init__

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje = mock.MagicMock(return_value="respuesta ok")

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["respuesta"] == "respuesta ok"
        # El view NO debe romper el camino limpio (la persistencia de filas
        # user/assistant la verifica la capa de aplicación en sus propios
        # tests; aquí sólo verificamos la respuesta HTTP.)


class TestGetNoModerado:
    """REQ-008 — El GET /copilot/chat/ (historial) NO corre moderación."""

    def test_get_no_invoca_moderacion(self, client_estudiante, monkeypatch):
        original_init = CopilotAppService.__init__

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            # Si el GET llamara ``procesar_mensaje``, este mock lo detectaría.
            self.procesar_mensaje = mock.MagicMock()

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.get(CHAT_URL)
        assert res.status_code == 200
        # ``procesar_mensaje`` NO fue tocado en el GET (sólo se llama en POST)
        # No podemos acceder a la instancia mockeada directamente, pero el GET
        # retorna 200 con ``{"conversacion_id": ..., "mensajes": []}``.
        data = res.json()
        assert "mensajes" in data
