"""Tests for the moderation wiring in CopilotAppService (PR 2,
copilot-content-moderation, Phase 2.1).

Wires ``ModeracionServicio`` (PR 1a) into ``procesar_mensaje`` (blocking) and
``procesar_mensaje_stream`` (SSE), with the B + D hooks on the streaming path.

The application service is the orchestration layer. These tests inject a fake
``ModeracionServicio`` via the constructor (no real OpenAI, no real word list)
and assert:

- Input STRONG: ``ContenidoBloqueadoError(razon="strong_list")`` raised, no
  user row persisted, no LLM call, no credits.
- Input LIGHT: censored text persisted and sent to LLM.
- Input CLEAN: original text persisted and sent to LLM.
- Input OpenAI-flagged: ``ContenidoBloqueadoError(razon="openai_input")``
  raised, no LLM call, no user row.
- Output flagged (blocking): CANNED_REFUSAL persisted + returned; raw reply
  discarded.
- Output clean: LLM reply persisted and returned unchanged.
- Feature flag off: no moderation call.

Strict TDD conventions: tests written FIRST (RED), then minimal implementation
(GREEN), then triangulation. The fake ``ModeracionServicio`` is a thin stub
that satisfies the public Protocol (``.evaluar_input(texto, *, request_id="")``
and ``.sanitizar(texto, resultado)``) so the application service contract is
pinned by the tests, not by re-implementing the domain service here.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest import mock

import pytest

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import ContenidoBloqueadoError
from apps.copilot.domain.moderation import (
    CANNED_REFUSAL,
    Severidad,
)
from apps.copilot.infrastructure.models import MensajeCopilot
from tests.factories import EstudianteFactory


# --------------------------------------------------------------------------- #
# Fakes — focused stubs that satisfy the protocol with NO behavior we don't
# explicitly set. This keeps the test boundary tight.
# --------------------------------------------------------------------------- #
@dataclass
class _FakeListProvider:
    """Fake ``ProveedorListaDura``. Returns whatever the test wires."""

    resultado: tuple[Severidad, str] | None = None

    def escanear(self, texto: str) -> tuple[Severidad, str] | None:
        return self.resultado


@dataclass
class _FakeOpenAIProvider:
    """Fake ``ProveedorModeracionExterno``. Returns whatever the test wires.

    ``clasificar`` is a function on the provider — the app service calls it
    directly for the output check.
    """

    input_result: bool = False
    output_result: bool = False
    raise_on_input: Exception | None = None
    raise_on_output: Exception | None = None
    input_call_count: int = 0
    output_call_count: int = 0
    last_input: str = ""
    last_output: str = ""

    def clasificar(self, texto: str) -> bool:
        # The app service uses ONE provider for BOTH input (via
        # ``evaluar_input``) and output (via the helper). We can't reliably
        # distinguish them by ``texto`` alone, so tests use a ``mock.patch``
        # on ``_FakeOpenAIProvider.clasificar`` when they need to set
        # different return values per call. This default impl is enough
        # for tests that just want a simple False return.
        return False


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _subir_rate_limit(monkeypatch):
    """Sube los topes por hora/sesión para que la lógica de moderación no se
    confunda con la del rate limit o de sesión."""
    monkeypatch.setattr(CopilotAppService, "MAX_MENSAJES_POR_HORA", 1000)
    monkeypatch.setattr(CopilotAppService, "MAX_MENSAJES_POR_SESION", 1000)


@pytest.fixture
def fake_openai():
    """Mock del cliente de chat completions (NO el de moderación)."""
    instance = mock.MagicMock()
    instance.chat_completion.return_value = ("respuesta limpia", 42)
    instance.chat_completion_stream.return_value = iter(["respuesta", " ", "limpia"])
    return instance


@pytest.fixture
def fake_openai_moderation():
    """Mock del cliente de moderación (provider externo)."""
    return _FakeOpenAIProvider()


@pytest.fixture
def fake_wordlist():
    """Mock del provider de lista dura."""
    return _FakeListProvider()


@pytest.fixture
def fake_moderation_service(fake_wordlist, fake_openai_moderation, monkeypatch):
    """Construye un ``ModeracionServicio`` real con providers fakeados.

    Los tests que quieren cambiar el resultado de ``clasificar`` por llamada
    usan ``mock.patch.object`` sobre ``fake_openai_moderation.clasificar``.
    """
    from apps.copilot.domain.moderation import ModeracionServicio

    return ModeracionServicio(
        proveedor_lista_dura=fake_wordlist,
        proveedor_moderacion_externo=fake_openai_moderation,
        habilitado=True,
    )


@pytest.fixture
def service(fake_openai, fake_moderation_service):
    return CopilotAppService(
        openai_client=fake_openai,
        academic_data_service=mock.MagicMock(),
        moderation_service=fake_moderation_service,
    )


@pytest.fixture
def service_flag_off(fake_openai, fake_wordlist, fake_openai_moderation):
    """Service con ``COPILOT_MODERATION_ENABLED=False`` (vía ModeracionServicio
    con ``habilitado=False``)."""
    from apps.copilot.domain.moderation import ModeracionServicio

    svc = ModeracionServicio(
        proveedor_lista_dura=fake_wordlist,
        proveedor_moderacion_externo=fake_openai_moderation,
        habilitado=False,
    )
    return CopilotAppService(
        openai_client=fake_openai,
        academic_data_service=mock.MagicMock(),
        moderation_service=svc,
    )


@pytest.fixture
def estudiante(db):
    user = EstudianteFactory()
    user.save()
    return user


# --------------------------------------------------------------------------- #
# T2.1 / T2.2 — Input STRONG: rechazo sin LLM, sin persistencia
# --------------------------------------------------------------------------- #
class TestInputStrong:
    def test_input_strong_levanta_contenido_bloqueado(self, service, estudiante, fake_wordlist):
        """Input con match STRONG debe levantar ``ContenidoBloqueadoError('strong_list')``."""
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            service.procesar_mensaje(estudiante, "eres un pendejo")
        assert excinfo.value.razon == "strong_list"

    def test_input_strong_persiste_el_mensaje_censurado(self, service, estudiante, fake_wordlist):
        """Issue 6: el turno queda registrado, pero con el texto ENMASCARADO.

        Cambia el contrato previo (que no persistía nada): el usuario debe ver
        su mensaje censurado en el chat, y al recargar el historial tiene que
        mostrar exactamente eso. La palabra original nunca se guarda.
        """
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError):
            service.procesar_mensaje(estudiante, "eres un pendejo")

        mensajes = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER)
        assert mensajes.count() == 1
        assert mensajes.first().contenido == "eres un ***"
        assert "pendejo" not in mensajes.first().contenido

    def test_input_strong_expone_censurado_y_respuesta_en_la_excepcion(
        self, service, estudiante, fake_wordlist
    ):
        """La excepción transporta lo que la vista necesita devolver al cliente."""
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            service.procesar_mensaje(estudiante, "eres un pendejo")

        assert excinfo.value.contenido_censurado == "eres un ***"
        assert "No puedo responder una pregunta en esos términos" in excinfo.value.respuesta

    def test_input_strong_no_llama_al_llm(self, service, estudiante, fake_openai, fake_wordlist):
        """Input con match STRONG NO debe llamar a ``chat_completion``."""
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError):
            service.procesar_mensaje(estudiante, "eres un pendejo")
        fake_openai.chat_completion.assert_not_called()

    def test_input_strong_persiste_rechazo_segun_el_rol(self, service, estudiante, fake_wordlist):
        """Issue 6: la respuesta guardada es el rechazo redactado para su rol."""
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError):
            service.procesar_mensaje(estudiante, "eres un pendejo")

        respuestas = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT)
        assert respuestas.count() == 1
        contenido = respuestas.first().contenido
        assert "No puedo responder una pregunta en esos términos" in contenido
        # El rol estudiante ve las áreas en las que el copilot SÍ puede ayudarlo
        assert "tus calificaciones" in contenido


# --------------------------------------------------------------------------- #
# T2.3 / T2.4 — Input LIGHT: censura y pasa al LLM
# --------------------------------------------------------------------------- #
class TestInputLight:
    def test_input_light_persiste_texto_censurado(self, service, estudiante, fake_wordlist):
        """Input con match LIGHT persiste la versión censurada (no la original)."""
        fake_wordlist.resultado = (Severidad.LIGHT, "dame mi *** de notas")

        service.procesar_mensaje(estudiante, "dame mi mierda de notas")
        user_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER).first()
        assert user_msg is not None
        assert user_msg.contenido == "dame mi *** de notas"

    def test_input_light_pasa_texto_censurado_al_llm(
        self, service, estudiante, fake_openai, fake_wordlist
    ):
        """Input con match LIGHT pasa la versión censurada al LLM (no la original)."""
        fake_wordlist.resultado = (Severidad.LIGHT, "dame mi *** de notas")

        service.procesar_mensaje(estudiante, "dame mi mierda de notas")
        # El segundo argumento posicional a ``chat_completion`` es ``messages``;
        # la system_prompt es el primero. El contenido censurado va dentro de
        # los messages, en la última entrada user.
        fake_openai.chat_completion.assert_called_once()
        call_args = fake_openai.chat_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[1]
        last_user_msg = [m for m in messages if m["rol"] == "user"][-1]
        assert last_user_msg["contenido"] == "dame mi *** de notas"

    def test_input_light_persiste_respuesta_del_llm(
        self, service, estudiante, fake_openai, fake_wordlist
    ):
        """Input con match LIGHT persiste la respuesta del LLM tal cual."""
        fake_wordlist.resultado = (Severidad.LIGHT, "dame mi *** de notas")
        fake_openai.chat_completion.return_value = ("tu promedio es 18", 100)

        service.procesar_mensaje(estudiante, "dame mi mierda de notas")
        assistant_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert assistant_msg is not None
        assert assistant_msg.contenido == "tu promedio es 18"

    def test_input_light_retorna_respuesta_del_llm(
        self, service, estudiante, fake_openai, fake_wordlist
    ):
        """Input con match LIGHT retorna la respuesta del LLM al caller."""
        fake_wordlist.resultado = (Severidad.LIGHT, "dame mi *** de notas")
        fake_openai.chat_completion.return_value = ("tu promedio es 18", 100)

        result = service.procesar_mensaje(estudiante, "dame mi mierda de notas")
        assert result == "tu promedio es 18"


# --------------------------------------------------------------------------- #
# T2.5 / T2.6 — Input CLEAN: pasa al LLM sin tocar
# --------------------------------------------------------------------------- #
class TestInputClean:
    def test_input_clean_persiste_texto_original(self, service, estudiante, fake_wordlist):
        """Input CLEAN persiste el texto original sin censura."""
        fake_wordlist.resultado = None  # sin match

        service.procesar_mensaje(estudiante, "hola, ¿cuál es mi promedio?")
        user_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER).first()
        assert user_msg is not None
        assert user_msg.contenido == "hola, ¿cuál es mi promedio?"

    def test_input_clean_pasa_texto_original_al_llm(
        self, service, estudiante, fake_openai, fake_wordlist
    ):
        """Input CLEAN pasa el texto original al LLM sin modificarlo."""
        fake_wordlist.resultado = None

        service.procesar_mensaje(estudiante, "hola mundo")
        fake_openai.chat_completion.assert_called_once()
        call_args = fake_openai.chat_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[1]
        last_user_msg = [m for m in messages if m["rol"] == "user"][-1]
        assert last_user_msg["contenido"] == "hola mundo"


# --------------------------------------------------------------------------- #
# T2.7 / T2.8 — Input OpenAI-flagged: rechazo sin LLM
# --------------------------------------------------------------------------- #
class TestInputOpenAIFlagged:
    def test_input_openai_flagged_levanta_contenido_bloqueado(
        self, service, estudiante, fake_wordlist, fake_openai_moderation
    ):
        """Input CLEAN en lista + OpenAI ``flagged=True`` → ContenidoBloqueadoError."""
        fake_wordlist.resultado = None
        fake_openai_moderation.input_result = True
        # ``evaluar_input`` llama al provider; mockeamos el método.
        with mock.patch.object(
            fake_openai_moderation, "clasificar", return_value=True
        ) as mock_clasificar:
            with pytest.raises(ContenidoBloqueadoError) as excinfo:
                service.procesar_mensaje(estudiante, "mensaje semánticamente malo")
            assert excinfo.value.razon == "openai_input"
            assert mock_clasificar.called

    def test_input_openai_flagged_persiste_turno_con_rechazo(
        self, service, estudiante, fake_wordlist, fake_openai_moderation
    ):
        """Issue 6: sin match de lista no hay nada que enmascarar, pero el turno
        igual queda registrado con el rechazo por rol."""
        fake_wordlist.resultado = None
        with mock.patch.object(fake_openai_moderation, "clasificar", return_value=True):
            with pytest.raises(ContenidoBloqueadoError):
                service.procesar_mensaje(estudiante, "mensaje semánticamente malo")

        usuario_msgs = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER)
        assert usuario_msgs.count() == 1
        assert usuario_msgs.first().contenido == "mensaje semánticamente malo"
        asistente = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert "No puedo responder una pregunta en esos términos" in asistente.contenido

    def test_input_openai_flagged_no_llama_al_llm(
        self, service, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """Input OpenAI-flagged NO debe llamar a ``chat_completion``."""
        fake_wordlist.resultado = None
        with mock.patch.object(fake_openai_moderation, "clasificar", return_value=True):
            with pytest.raises(ContenidoBloqueadoError):
                service.procesar_mensaje(estudiante, "mensaje semánticamente malo")
        fake_openai.chat_completion.assert_not_called()


# --------------------------------------------------------------------------- #
# T2.9 / T2.10 — Output flagged (blocking): reemplaza con CANNED_REFUSAL
# --------------------------------------------------------------------------- #
class TestOutputFlagged:
    def test_output_flagged_persiste_canned_refusal(
        self, service, estudiante, fake_openai, fake_openai_moderation, fake_wordlist
    ):
        """Output flagged por OpenAI → persiste CANNED_REFUSAL (no la respuesta cruda)."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion.return_value = ("respuesta con contenido flagged", 42)
        # El input sale clean (la lista no matchea) y el output sale flagged
        with mock.patch.object(
            fake_openai_moderation, "clasificar", side_effect=[False, True]
        ) as mock_clasificar:
            result = service.procesar_mensaje(estudiante, "consulta normal")

        # 2 llamadas a clasificar: 1 input (False) + 1 output (True)
        assert mock_clasificar.call_count == 2
        assert result == CANNED_REFUSAL
        assistant_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert assistant_msg is not None
        assert assistant_msg.contenido == CANNED_REFUSAL
        # El contenido crudo NUNCA debe aparecer en la DB
        assert not MensajeCopilot.objects.filter(
            rol=MensajeCopilot.Rol.ASSISTANT,
            contenido="respuesta con contenido flagged",
        ).exists()

    def test_output_flagged_retorna_canned_refusal(
        self, service, estudiante, fake_openai, fake_openai_moderation, fake_wordlist
    ):
        """Output flagged → el método retorna CANNED_REFUSAL al caller."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion.return_value = ("respuesta mala", 42)
        with mock.patch.object(fake_openai_moderation, "clasificar", side_effect=[False, True]):
            result = service.procesar_mensaje(estudiante, "consulta normal")
        assert result == CANNED_REFUSAL


# --------------------------------------------------------------------------- #
# T2.11 / T2.12 — Output clean: pasa al LLM
# --------------------------------------------------------------------------- #
class TestOutputClean:
    def test_output_clean_persiste_respuesta_llm(
        self, service, estudiante, fake_openai, fake_openai_moderation, fake_wordlist
    ):
        """Output clean → persiste la respuesta del LLM tal cual."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion.return_value = ("respuesta limpia", 42)
        with mock.patch.object(fake_openai_moderation, "clasificar", return_value=False):
            service.procesar_mensaje(estudiante, "consulta normal")
        assistant_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert assistant_msg is not None
        assert assistant_msg.contenido == "respuesta limpia"

    def test_output_clean_retorna_respuesta_llm(
        self, service, estudiante, fake_openai, fake_openai_moderation, fake_wordlist
    ):
        """Output clean → retorna la respuesta del LLM al caller."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion.return_value = ("respuesta limpia", 42)
        with mock.patch.object(fake_openai_moderation, "clasificar", return_value=False):
            result = service.procesar_mensaje(estudiante, "consulta normal")
        assert result == "respuesta limpia"


# --------------------------------------------------------------------------- #
# T2.7-feature-flag — Bypass total cuando COPILOT_MODERATION_ENABLED=False
# --------------------------------------------------------------------------- #
class TestFeatureFlagOff:
    def test_feature_flag_off_no_llama_moderacion_input(
        self, service_flag_off, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """Con ``habilitado=False`` en el ModeracionServicio, el input NO se modera."""
        # Si la moderación corriera, ``fake_wordlist.resultado`` (None) haría
        # que se llame al OpenAI provider — lo cual no debe pasar.
        with mock.patch.object(fake_openai_moderation, "clasificar") as mock_clasificar:
            service_flag_off.procesar_mensaje(estudiante, "cualquier cosa")
        mock_clasificar.assert_not_called()

    def test_feature_flag_off_pasa_input_sin_tocar(
        self, service_flag_off, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """Con flag off, el input llega tal cual al LLM y a la DB aunque la lista
        diga STRONG — el bypass es TOTAL (REQ-007)."""
        fake_wordlist.resultado = (Severidad.STRONG, "should not be checked")

        with mock.patch.object(fake_openai_moderation, "clasificar") as mock_clasificar:
            result = service_flag_off.procesar_mensaje(estudiante, "input directo")

        # Input persistido tal cual (sin moderación)
        user_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER).first()
        assert user_msg is not None
        assert user_msg.contenido == "input directo"
        # Y la respuesta del LLM también vuelve tal cual (sin output check)
        assert result == "respuesta limpia"
        mock_clasificar.assert_not_called()


# --------------------------------------------------------------------------- #
# T2.13 / T2.14 — SSE D hook: abort en el primer chunk flagged
# --------------------------------------------------------------------------- #
class TestSSEHookD:
    def test_sse_d_aborta_en_primer_chunk_flagged(
        self, service, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """SSE: si el primer chunk del LLM es flagged, NO se emiten deltas, se
        emite un único ``replacement`` y la DB guarda ``CANNED_REFUSAL``."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion_stream.return_value = iter(["mierda", " de", " notas"])
        # 1ª llamada: input check (False); 2ª: D check (True)
        with mock.patch.object(fake_openai_moderation, "clasificar", side_effect=[False, True]):
            stream = service.procesar_mensaje_stream(estudiante, "consulta normal")
            events = list(stream)

        # El primer yield debe ser el replacement marker (no un delta)
        assert len(events) == 1
        assert isinstance(events[0], dict)
        assert events[0]["type"] == "replacement"
        assert events[0]["text"] == CANNED_REFUSAL

        # El assistant persistido es CANNED_REFUSAL, NO "mierda de notas"
        assistant_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert assistant_msg is not None
        assert assistant_msg.contenido == CANNED_REFUSAL
        assert not MensajeCopilot.objects.filter(
            rol=MensajeCopilot.Rol.ASSISTANT,
            contenido="mierda de notas",
        ).exists()

    def test_sse_d_no_emite_deltas_al_cliente(
        self, service, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """SSE D hook: el cliente NO debe ver ningún chunk del LLM (sólo el replacement)."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion_stream.return_value = iter(["mierda", " de", " notas"])
        with mock.patch.object(fake_openai_moderation, "clasificar", side_effect=[False, True]):
            events = list(service.procesar_mensaje_stream(estudiante, "consulta"))

        # No debe haber strings (deltas) en la secuencia
        assert all(isinstance(e, dict) for e in events)
        assert all(e.get("type") == "replacement" for e in events)


# --------------------------------------------------------------------------- #
# T2.15 / T2.16 — SSE B hook: replacement después del stream
# --------------------------------------------------------------------------- #
class TestSSEHookB:
    def test_sse_b_emite_replacement_despues_de_deltas(
        self, service, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """SSE: si los chunks son clean pero la respuesta final es flagged, se
        emiten los deltas Y al final un evento ``replacement``."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion_stream.return_value = iter(["Hola", " mundo", " flagged"])
        # 1ª: input (False); 2ª: D check del primer chunk (False); 3ª: B check (True)
        with mock.patch.object(
            fake_openai_moderation,
            "clasificar",
            side_effect=[False, False, True],
        ):
            events = list(service.procesar_mensaje_stream(estudiante, "consulta"))

        # 3 deltas + 1 replacement
        assert len(events) == 4
        assert events[0] == "Hola"
        assert events[1] == " mundo"
        assert events[2] == " flagged"
        assert events[3] == {"type": "replacement", "text": CANNED_REFUSAL}

        # DB: persiste CANNED_REFUSAL, NO el contenido crudo
        assistant_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert assistant_msg is not None
        assert assistant_msg.contenido == CANNED_REFUSAL
        assert not MensajeCopilot.objects.filter(
            rol=MensajeCopilot.Rol.ASSISTANT,
            contenido="Hola mundo flagged",
        ).exists()

    def test_sse_b_clean_no_emite_replacement(
        self, service, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """SSE B hook clean: emite los deltas y NO emite replacement."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion_stream.return_value = iter(["Hola", " mundo"])
        # input (False) + D (False) + B (False)
        with mock.patch.object(
            fake_openai_moderation,
            "clasificar",
            side_effect=[False, False, False],
        ):
            events = list(service.procesar_mensaje_stream(estudiante, "consulta"))

        assert events == ["Hola", " mundo"]
        # NO replacement
        assert not any(isinstance(e, dict) and e.get("type") == "replacement" for e in events)

    def test_sse_stream_vacio_no_modera(
        self, service, estudiante, fake_openai, fake_wordlist, fake_openai_moderation
    ):
        """SSE stream vacío: NO se ejecuta B check, NO se persiste fila del asistente."""
        fake_wordlist.resultado = None
        fake_openai.chat_completion_stream.return_value = iter([])
        with mock.patch.object(
            fake_openai_moderation, "clasificar", return_value=False
        ) as mock_clasificar:
            events = list(service.procesar_mensaje_stream(estudiante, "consulta"))

        assert events == []
        # El B check NO debe correr para streams vacíos
        assert mock_clasificar.call_count == 1  # sólo el input check
        # No se persiste assistant
        assert MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).count() == 0


# --------------------------------------------------------------------------- #
# T2.17 / T2.18 — SSE input STRONG: rechazo sincrónico, NO se llama al LLM
# --------------------------------------------------------------------------- #
class TestSSEInputStrong:
    def test_sse_input_strong_levanta_sincronicamente(
        self, service, estudiante, fake_openai, fake_wordlist
    ):
        """SSE: input STRONG → ContenidoBloqueadoError ANTES de que el generador se cree."""
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            service.procesar_mensaje_stream(estudiante, "eres un pendejo")
        assert excinfo.value.razon == "strong_list"
        # Y NO se llama a ``chat_completion_stream`` (ni se genera un generator)
        fake_openai.chat_completion_stream.assert_not_called()

    def test_sse_input_strong_persiste_censurado_y_rechazo(
        self, service, estudiante, fake_wordlist
    ):
        """Issue 6: el path SSE persiste el mismo turno censurado que el bloqueante."""
        fake_wordlist.resultado = (Severidad.STRONG, "eres un ***")

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            service.procesar_mensaje_stream(estudiante, "eres un pendejo")

        assert excinfo.value.contenido_censurado == "eres un ***"
        usuario_msg = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.USER).first()
        assert usuario_msg.contenido == "eres un ***"
        asistente = MensajeCopilot.objects.filter(rol=MensajeCopilot.Rol.ASSISTANT).first()
        assert "No puedo responder una pregunta en esos términos" in asistente.contenido

    def test_sse_input_clean_retorna_generator(self, service, estudiante, fake_wordlist):
        """SSE input CLEAN → ``procesar_mensaje_stream`` retorna un generator."""
        fake_wordlist.resultado = None

        result = service.procesar_mensaje_stream(estudiante, "hola")
        # Un generator es iterable (no se materializa con sólo crearlo)
        import types

        assert isinstance(result, types.GeneratorType)
        # Y consumirlo produce deltas
        events = list(result)
        assert "respuesta" in events
