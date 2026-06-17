"""SSE walker tests for the moderation replacement event (PR 2,
copilot-content-moderation, Phase 2.2 — presentation).

Drives the ``CopilotChatStreamView`` end-to-end with a fake
``CopilotAppService`` whose ``procesar_mensaje_stream`` returns a generator
matching the B and D hook scenarios. The response is walked by a tiny
hand-rolled SSE parser that splits on ``\\n\\n`` and parses each ``data:``
payload. The parser asserts the EXACT event order.

These tests cover the SSE event protocol contract documented in
``design.md`` §SSE + Output Moderation Design (B + D):

    | Event         | Payload                                         |
    |---------------|-------------------------------------------------|
    | ``delta``     | ``{"delta": "<chunk>"}``                        |
    | ``replacement``| ``{"replacement": "<CANNED_REFUSAL>"}``        |
    | ``[DONE]``    | (verbatim SSE terminator)                        |

D path: deltas go UNEMITTED; the FIRST event is a ``replacement`` followed by
``[DONE]``. B path: deltas are streamed, then a final ``replacement`` is
emitted, then ``[DONE]``.

The widget patch (``templates/copilot/widget.html``) is the consumer of this
contract; the contract is what we test here (the widget has no Alpine test
infrastructure in this repo — see ``openspec/config.yaml`` e2e status
``not planned``).
"""

from __future__ import annotations

import json
from typing import Any
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.moderation import CANNED_REFUSAL
from tests.factories import EstudianteFactory


STREAM_URL = reverse("copilot:chat_stream")


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #
def _walk_sse(response) -> list[dict[str, Any] | str]:
    """Parsea el body de un ``StreamingHttpResponse`` SSE en eventos.

    Devuelve una lista de payloads en orden. Cada payload es:
        - un ``dict`` cuando el ``data:`` es JSON parseable.
        - el string ``"[DONE]"`` para el terminador SSE verbatim.
    """
    body = b"".join(response.streaming_content).decode("utf-8")
    events: list[dict[str, Any] | str] = []
    for raw_event in body.split("\n\n"):
        if not raw_event:
            continue
        for line in raw_event.split("\n"):
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                events.append("[DONE]")
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                events.append({"_raw": payload})
    return events


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


# -------------------------------------------------------------------- #
# T2.21 / T2.22 — SSE input rejection: returns JSON (not a stream)
# -------------------------------------------------------------------- #
class TestSSEInputRejection:
    """Cuando el input es rechazado por moderación, la vista NO retorna un
    stream — retorna JSON HTTP 200 con la canned refusal. Esto es porque
    el raise del input check es sincrónico (ocurre antes de que se cree el
    generator)."""

    def test_input_strong_retorna_json_no_stream(self, client_estudiante, monkeypatch):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError

        original_init = CopilotAppService.__init__

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje_stream = mock.MagicMock(
                side_effect=ContenidoBloqueadoError(razon="strong_list")
            )

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            STREAM_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        # El content-type es JSON, no text/event-stream
        assert "json" in res["Content-Type"]
        data = res.json()
        assert data["respuesta"] == CANNED_REFUSAL

    def test_input_openai_flagged_retorna_json_no_stream(self, client_estudiante, monkeypatch):
        from apps.copilot.domain.exceptions import ContenidoBloqueadoError

        original_init = CopilotAppService.__init__

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje_stream = mock.MagicMock(
                side_effect=ContenidoBloqueadoError(razon="openai_input")
            )

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            STREAM_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["respuesta"] == CANNED_REFUSAL


# -------------------------------------------------------------------- #
# T2.24 / T2.25 — SSE walker: B hook (post-stream replacement)
# -------------------------------------------------------------------- #
class TestSSEWalkerBPath:
    """B hook: el LLM streamea deltas normales, luego la moderación de salida
    detecta la respuesta ensamblada como flagged, y se emite un evento
    ``replacement`` ANTES del ``[DONE]``."""

    def test_b_path_event_order_deltas_replacement_done(self, client_estudiante, monkeypatch):
        original_init = CopilotAppService.__init__

        def fake_stream(self, *args, **kwargs):
            yield "Hola"
            yield " "
            yield "mundo"
            yield {"type": "replacement", "text": CANNED_REFUSAL}

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje_stream = mock.MagicMock(side_effect=fake_stream)

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            STREAM_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        assert "event-stream" in res["Content-Type"]

        events = _walk_sse(res)
        # 3 deltas + 1 replacement + [DONE]
        assert len(events) == 5
        assert events[0] == {"delta": "Hola"}
        assert events[1] == {"delta": " "}
        assert events[2] == {"delta": "mundo"}
        assert events[3] == {"replacement": CANNED_REFUSAL}
        assert events[4] == "[DONE]"


# -------------------------------------------------------------------- #
# T2.26 / T2.27 — SSE walker: D hook (first-chunk abort)
# -------------------------------------------------------------------- #
class TestSSEWalkerDPath:
    """D hook: el primer chunk del LLM es flagged, se aborta el stream sin
    reenviar NINGÚN delta al cliente, y se emite SOLO el evento
    ``replacement`` antes del ``[DONE]``."""

    def test_d_path_event_order_replacement_done_sin_deltas(self, client_estudiante, monkeypatch):
        original_init = CopilotAppService.__init__

        def fake_stream(self, *args, **kwargs):
            # El D hook corre en el service (no en la vista), por lo que el
            # generator del service ya emite sólo el replacement marker y
            # return. La vista traduce el marker a un evento ``replacement``.
            yield {"type": "replacement", "text": CANNED_REFUSAL}

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje_stream = mock.MagicMock(side_effect=fake_stream)

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            STREAM_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        assert "event-stream" in res["Content-Type"]

        events = _walk_sse(res)
        # 1 replacement + [DONE] (NO deltas)
        assert len(events) == 2
        assert events[0] == {"replacement": CANNED_REFUSAL}
        assert events[1] == "[DONE]"
        # Sanity: no hay NINGÚN evento ``delta``
        assert not any("delta" in e for e in events if isinstance(e, dict))


# -------------------------------------------------------------------- #
# Sanity: el camino limpio del SSE emite sólo deltas + [DONE]
# -------------------------------------------------------------------- #
class TestSSEWalkerClean:
    def test_clean_path_solo_deltas_y_done(self, client_estudiante, monkeypatch):
        original_init = CopilotAppService.__init__

        def fake_stream(self, *args, **kwargs):
            yield "Hola"
            yield " "
            yield "mundo"

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje_stream = mock.MagicMock(side_effect=fake_stream)

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            STREAM_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        events = _walk_sse(res)
        assert events == [
            {"delta": "Hola"},
            {"delta": " "},
            {"delta": "mundo"},
            "[DONE]",
        ]


# -------------------------------------------------------------------- #
# REQ-005 — la payload del replacement es byte-locked con CANNED_REFUSAL
# -------------------------------------------------------------------- #
class TestReplacementPayloadByteLocked:
    def test_replacement_payload_es_exactamente_canned_refusal(
        self, client_estudiante, monkeypatch
    ):
        original_init = CopilotAppService.__init__

        def fake_stream(self, *args, **kwargs):
            yield {"type": "replacement", "text": CANNED_REFUSAL}

        def _init(self, **kwargs):
            original_init(self, **kwargs)
            self.procesar_mensaje_stream = mock.MagicMock(side_effect=fake_stream)

        monkeypatch.setattr(CopilotAppService, "__init__", _init)

        res = client_estudiante.post(
            STREAM_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        events = _walk_sse(res)
        # El primer evento (no-DONE) es el replacement; su payload es byte-locked
        replacement_event = events[0]
        assert isinstance(replacement_event, dict)
        assert "replacement" in replacement_event
        # Byte-by-byte equality
        assert replacement_event["replacement"] == CANNED_REFUSAL
        # La forma JSON es exactamente ``{"replacement": "<texto>"}``
        body = b"".join(res.streaming_content).decode("utf-8")
        # Encuentra la primera línea ``data:`` que NO sea ``[DONE]``
        for line in body.split("\n"):
            if line.startswith("data: ") and line != "data: [DONE]":
                payload = line[6:]
                parsed = json.loads(payload)
                assert set(parsed.keys()) == {"replacement"}
                assert parsed["replacement"] == CANNED_REFUSAL
                break
