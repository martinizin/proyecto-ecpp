"""OpenAI client wrapper for the copilot.

Centralises the calls to the OpenAI Chat Completions API. Kept thin so
the copilot can be tested with `unittest.mock.patch` without hitting
the network.
"""

from __future__ import annotations

from django.conf import settings
from openai import OpenAI


class OpenAIClient:
    """Thin wrapper around the OpenAI Python SDK.

    Uses `settings.OPENAI_API_KEY` and `settings.COPILOT_MODEL`. The
    client instance is created lazily so the rest of the copilot code
    can still be imported in environments where the key is missing
    (e.g. CI, tests).
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self._model = model if model is not None else settings.COPILOT_MODEL
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> tuple[str, int]:
        """Send a chat completion request and return (content, total_tokens)."""
        formatted = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            formatted.append({"role": msg["rol"], "content": msg["contenido"]})

        response = self.client.chat.completions.create(
            model=self._model,
            messages=formatted,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return content, tokens
