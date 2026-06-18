"""Unit tests for OpenAIModerationClient (PR 1b, copilot-content-moderation).

Concrete implementation of the ``ProveedorModeracionExterno`` Protocol declared
in ``apps.copilot.domain.moderation``. The client wraps the OpenAI Python SDK
``moderations.create`` call and returns ``True`` when the input is flagged.

Failure semantics (locked by the domain service in PR 1a):
- ``openai.APIError`` family (Timeout, Connection, 4xx, 5xx) PROPAGATES. The
  domain ``ModeracionServicio.evaluar_input`` / ``evaluar_output`` catches it
  and applies fail-OPEN (input) / skip (output) per REQ-009.
- Malformed response body (missing ``results``, missing ``flagged``, non-JSON)
  is a different category — the API returned 200 OK but the body is unusable.
  The client returns ``False`` and logs WARNING. This is the wrapper-layer
  fail-open per spec REQ-009.

The OpenAI SDK is patched via ``unittest.mock`` — no real HTTP calls.
"""

from __future__ import annotations

from unittest import mock

import pytest


def _make_flagged_response(flagged: bool, categories: dict | None = None):
    """Helper: builds a mock OpenAI Moderation response object."""
    response = mock.MagicMock()
    response.results = [mock.MagicMock()]
    response.results[0].flagged = flagged
    if categories is not None:
        response.results[0].categories = categories
    return response


# --------------------------------------------------------------------------- #
# T1b.13 + T1b.14 — Success path (200 OK, flagged True / False)
# --------------------------------------------------------------------------- #
class TestOpenAIModerationClientSuccess:
    """El happy path: el SDK responde 200 con ``flagged`` parseable."""

    def test_200_flagged_true_retorna_true(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.return_value = _make_flagged_response(flagged=True)
            resultado = client.clasificar("texto mal")
        assert resultado is True

    def test_200_flagged_false_retorna_false(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.return_value = _make_flagged_response(flagged=False)
            resultado = client.clasificar("consulta normal")
        assert resultado is False

    def test_llama_sdk_con_modelo_correcto(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test", model="omni-moderation-latest")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.return_value = _make_flagged_response(flagged=False)
            client.clasificar("texto")
            # Verifica que el SDK fue llamado con input y model
            call_kwargs = mock_sdk.moderations.create.call_args.kwargs
            assert call_kwargs["input"] == "texto"
            assert call_kwargs["model"] == "omni-moderation-latest"

    def test_modelo_default_es_omni_moderation_latest(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.return_value = _make_flagged_response(flagged=False)
            client.clasificar("texto")
            call_kwargs = mock_sdk.moderations.create.call_args.kwargs
            assert call_kwargs["model"] == "omni-moderation-latest"


# --------------------------------------------------------------------------- #
# T1b.15 + T1b.16 — Malformed body: client returns False + log WARNING
# --------------------------------------------------------------------------- #
class TestOpenAIModerationClientMalformedBody:
    """Cuando la API responde 200 OK pero el body no tiene ``flagged`` parseable,
    el cliente retorna False y loggea WARNING (REQ-009 + design §Malformed body)."""

    def test_results_vacio_retorna_false(self, caplog):
        import logging

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        response = mock.MagicMock()
        response.results = []

        with caplog.at_level(logging.WARNING):
            with mock.patch.object(client, "_client") as mock_sdk:
                mock_sdk.moderations.create.return_value = response
                resultado = client.clasificar("texto")

        assert resultado is False
        assert any("malformed" in r.message.lower() for r in caplog.records)

    def test_result_sin_flagged_attr_retorna_false(self, caplog):
        import logging

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        response = mock.MagicMock()
        # results[0] no tiene atributo .flagged
        result_sin_flagged = mock.MagicMock(spec=[])
        response.results = [result_sin_flagged]

        with caplog.at_level(logging.WARNING):
            with mock.patch.object(client, "_client") as mock_sdk:
                mock_sdk.moderations.create.return_value = response
                resultado = client.clasificar("texto")

        assert resultado is False

    def test_flagged_none_retorna_false(self, caplog):
        import logging

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        response = mock.MagicMock()
        response.results = [mock.MagicMock()]
        response.results[0].flagged = None

        with caplog.at_level(logging.WARNING):
            with mock.patch.object(client, "_client") as mock_sdk:
                mock_sdk.moderations.create.return_value = response
                resultado = client.clasificar("texto")

        assert resultado is False


# --------------------------------------------------------------------------- #
# T1b.19 + T1b.20 — API errors propagate (domain layer handles fail-OPEN/skip)
# --------------------------------------------------------------------------- #
class TestOpenAIModerationClientAPIErrors:
    """Los errores de red/4xx/5xx/tiempo se propagan al dominio, que decide
    si hace fail-OPEN (input) o skip (output) per REQ-009."""

    def test_timeout_propagates(self):
        import openai

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.side_effect = openai.APITimeoutError("timeout")
            with pytest.raises(openai.APITimeoutError):
                client.clasificar("texto")

    def test_connection_error_propagates(self):
        import openai

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.side_effect = openai.APIConnectionError(
                request=mock.MagicMock()
            )
            with pytest.raises(openai.APIConnectionError):
                client.clasificar("texto")

    def test_bad_request_propagates(self):
        import openai

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.side_effect = openai.BadRequestError(
                message="bad",
                response=mock.MagicMock(status_code=400),
                body={},
            )
            with pytest.raises(openai.BadRequestError):
                client.clasificar("texto")

    def test_authentication_error_propagates(self):
        import openai

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.side_effect = openai.AuthenticationError(
                message="invalid key",
                response=mock.MagicMock(status_code=401),
                body={},
            )
            with pytest.raises(openai.AuthenticationError):
                client.clasificar("texto")

    def test_rate_limit_propagates(self):
        import openai

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.side_effect = openai.RateLimitError(
                message="rate",
                response=mock.MagicMock(status_code=429),
                body={},
            )
            with pytest.raises(openai.RateLimitError):
                client.clasificar("texto")

    def test_internal_server_error_propagates(self):
        import openai

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        with mock.patch.object(client, "_client") as mock_sdk:
            mock_sdk.moderations.create.side_effect = openai.InternalServerError(
                message="500",
                response=mock.MagicMock(status_code=500),
                body={},
            )
            with pytest.raises(openai.InternalServerError):
                client.clasificar("texto")


# --------------------------------------------------------------------------- #
# Constructor & configuration
# --------------------------------------------------------------------------- #
class TestOpenAIModerationClientConstructor:
    """Verifica que el constructor acepta api_key, model, timeout y los defaults."""

    def test_acepta_api_key_explicita(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-explicit")
        assert client is not None

    def test_acepta_model_explicito(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test", model="text-moderation-stable")
        # No raise = OK
        assert client is not None

    def test_acepta_timeout_explicito(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test", timeout=2.5)
        assert client is not None

    def test_default_model_es_omni_moderation_latest(self):
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        # Sin pasar model, el default debe ser omni-moderation-latest
        client = OpenAIModerationClient(api_key="sk-test")
        assert client.model == "omni-moderation-latest"

    def test_default_timeout_es_setting_o_5_segundos(self):
        """El default se lee de ``COPILOT_MODERATION_OPENAI_TIMEOUT_MS`` (1500ms
        = 1.5s en el entorno de test). Si la setting no existiera, el fallback
        sería 5.0s (constructor default)."""
        from django.conf import settings

        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test")
        # En el test env la setting existe con 1500ms → 1.5s
        assert client.timeout == settings.COPILOT_MODERATION_OPENAI_TIMEOUT_MS / 1000.0
        assert client.timeout == 1.5

    def test_timeout_explicito_sobreescribe_setting(self):
        """Pasar ``timeout`` al constructor siempre gana sobre la setting."""
        from apps.copilot.infrastructure.openai_moderation_client import (
            OpenAIModerationClient,
        )

        client = OpenAIModerationClient(api_key="sk-test", timeout=10.0)
        assert client.timeout == 10.0
