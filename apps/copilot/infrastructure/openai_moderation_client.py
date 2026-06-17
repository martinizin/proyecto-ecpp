"""OpenAI Moderation API client for the copilot moderation layer.

Concrete implementation of the ``ProveedorModeracionExterno`` Protocol declared
in ``apps.copilot.domain.moderation``. Wraps the OpenAI Python SDK's
``moderations.create`` call and returns ``True`` when the input is flagged.

Failure semantics (locked by the domain service in PR 1a):
- ``openai.APIError`` family (Timeout, Connection, 4xx, 5xx, RateLimit, etc.)
  PROPAGATES to the caller. The domain ``ModeracionServicio.evaluar_input``
  / ``evaluar_output`` catches it and applies fail-OPEN (input) / skip
  (output) per REQ-009.
- Malformed response body (missing ``results``, missing ``flagged``, etc.) is
  a different category — the API returned 200 OK but the body is unusable.
  The client returns ``False`` and logs WARNING. This is the wrapper-layer
  fail-open per spec REQ-009 / design §Malformed body.
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI


logger = logging.getLogger("apps.copilot.moderation.openai")


# Default model for OpenAI Moderation API (locked by design.md §Configuration).
DEFAULT_MODEL: str = "omni-moderation-latest"

# Default timeout in seconds (locked by orchestrator's PR 1b spec).
# Note: design.md suggests 1500 ms for production, but the constructor
# default exposed in PR 1b is 5.0 s as a safety net. The production wiring
# (PR 2) will read ``COPILOT_MODERATION_OPENAI_TIMEOUT_MS`` from settings
# (default 1500) and pass the converted value to this client.
DEFAULT_TIMEOUT_S: float = 5.0


class OpenAIModerationClient:
    """Thin wrapper around the OpenAI Moderation API.

    Matches ``ProveedorModeracionExterno`` from
    ``apps.copilot.domain.moderation``: exposes ``clasificar(texto) -> bool``.

    Constructor signature:
        - ``api_key``: OpenAI API key. ``None`` reads ``settings.OPENAI_API_KEY``.
        - ``model``: Moderation model name. Default ``"omni-moderation-latest"``.
        - ``timeout``: Per-call timeout in seconds. Default ``5.0``.

    The OpenAI SDK client is created eagerly in ``__init__`` to make the
    boundary mockable via ``mock.patch.object(client, "_client")``. This is a
    deliberate departure from ``OpenAIClient``'s lazy-init pattern: the
    moderation client is a hot-path dependency (called on every chat message)
    and a missing API key should surface as a clear ``OpenAIError`` on the
    first call rather than a delayed property access.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        # Lazy import: avoid Django settings import at module load (CI/tests
        # without DJANGO_SETTINGS_MODULE configured).
        from django.conf import settings

        self._api_key: str = (
            api_key if api_key is not None else getattr(settings, "OPENAI_API_KEY", "")
        )
        self._model: str = (
            model
            if model is not None
            else getattr(settings, "COPILOT_MODERATION_MODEL", DEFAULT_MODEL)
        )
        # ``timeout`` is in seconds (float). The legacy
        # ``COPILOT_MODERATION_OPENAI_TIMEOUT_MS`` setting (in ms) is the
        # preferred source of truth in production; if ``timeout`` is None and
        # the setting is present, convert ms → s. Otherwise fall back to the
        # public default.
        if timeout is not None:
            self._timeout_s: float = float(timeout)
        else:
            timeout_ms = getattr(settings, "COPILOT_MODERATION_OPENAI_TIMEOUT_MS", None)
            self._timeout_s = (
                float(timeout_ms) / 1000.0 if timeout_ms is not None else DEFAULT_TIMEOUT_S
            )
        # Public attributes for testability / introspection.
        self.api_key: str = self._api_key
        self.model: str = self._model
        self.timeout: float = self._timeout_s

        # Eager init: the moderation client is constructed in PR 2 with
        # explicit ``api_key``, so missing keys are surfaced as
        # ``openai.OpenAIError`` on the first call rather than a confusing
        # ``AttributeError`` from a None client.
        self._client: OpenAI = OpenAI(api_key=self._api_key)

    def clasificar(self, texto: str) -> bool:
        """Llama a ``moderations.create`` y devuelve ``True`` si el texto fue flagged.

        Raises:
            openai.APIError: familia completa (Timeout, Connection, 4xx, 5xx,
                RateLimit, etc.). El servicio de dominio las captura y aplica
                fail-OPEN (input) / skip (output) per REQ-009.

        Returns:
            bool: ``True`` si el API marcó el texto como flagged, ``False``
            en cualquier otro caso (clean o body malformado).
        """
        response = self._client.moderations.create(
            input=texto,
            model=self._model,
            timeout=self._timeout_s,
        )
        return self._parse_flagged(response)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_flagged(response: Any) -> bool:
        """Extrae ``flagged`` del response. Body malformado → ``False`` + WARNING.

        Body malformado incluye:
        - ``results`` vacío o None
        - ``results[0]`` sin atributo ``flagged``
        - ``flagged`` con valor None
        """
        try:
            results = getattr(response, "results", None)
            if not results:
                logger.warning(
                    "copilot.moderation.api.malformed",
                    extra={"reason": "empty_results"},
                )
                return False
            first = results[0]
            flagged = getattr(first, "flagged", None)
            if flagged is None:
                logger.warning(
                    "copilot.moderation.api.malformed",
                    extra={"reason": "missing_flagged"},
                )
                return False
            return bool(flagged)
        except (AttributeError, IndexError, TypeError) as exc:
            # Catch-all para shapes inesperados del SDK (versiones nuevas, etc.)
            logger.warning(
                "copilot.moderation.api.malformed",
                extra={
                    "reason": "unexpected_shape",
                    "error_class": type(exc).__name__,
                },
            )
            return False
