"""View tests for CopilotChatView and CopilotNuevaConversacionView (HU22).

Covers:
- Access control: anonymous → redirect/403, inspector/secretaria → 403,
  estudiante/docente → 200/201
- GET /copilot/chat/ returns the active conversation history
- POST /copilot/chat/ persists user + assistant messages
- POST /copilot/chat/ with empty body → 400
- POST /copilot/chat/ with too-long mensaje → 400
- POST /copilot/chat/ rate limit → 429
- POST /copilot/nueva-conversacion/ closes current + creates new

OpenAI is mocked so the test never hits the real API.
"""

import json
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse

from apps.copilot.application.services import CopilotAppService
from apps.copilot.infrastructure.models import (
    ConversacionCopilot,
    MensajeCopilot,
)
from tests.factories import (
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
)


CHAT_URL = reverse("copilot:chat")
NUEVA_URL = reverse("copilot:nueva_conversacion")


# -------------------------------------------------------------------- #
# Fixtures
# -------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _mock_openai(monkeypatch):
    """Mock OpenAIClient so procesar_mensaje never hits the real API."""
    fake = mock.MagicMock()
    fake.chat_completion.return_value = ("respuesta mock", 10)
    mock_data = mock.MagicMock()
    mock_data.obtener_datos.return_value = "datos mock"
    # PR 2 — mock del moderation service: bypass total (CLEAN en input y output).
    # Construimos un ModeracionServicio con providers que devuelven ``False``
    # siempre, así los tests legacy del view no se ven afectados por la
    # lógica de moderación.
    from apps.copilot.domain.moderation import ModeracionServicio

    class _NoopProvider:
        def escanear(self, texto):
            return None  # CLEAN

        def clasificar(self, texto):
            return False  # CLEAN

    mock_moderation = ModeracionServicio(
        proveedor_lista_dura=_NoopProvider(),
        proveedor_moderacion_externo=_NoopProvider(),
        habilitado=True,
    )
    monkeypatch.setattr(
        CopilotAppService,
        "__init__",
        lambda self, **kw: (
            setattr(self, "openai_client", fake),
            setattr(self, "academic_data_service", mock_data),
            setattr(self, "moderation_service", mock_moderation),
        )[-1],
    )


@pytest.fixture
def estudiante(db):
    user = EstudianteFactory()
    user.save()
    return user


@pytest.fixture
def docente(db):
    user = DocenteFactory()
    user.save()
    return user


@pytest.fixture
def inspector(db):
    user = InspectorFactory()
    user.save()
    return user


@pytest.fixture
def client_estudiante(estudiante):
    c = Client()
    c.force_login(estudiante)
    return c


@pytest.fixture
def client_docente(docente):
    c = Client()
    c.force_login(docente)
    return c


@pytest.fixture
def client_inspector(inspector):
    c = Client()
    c.force_login(inspector)
    return c


# -------------------------------------------------------------------- #
# Access control
# -------------------------------------------------------------------- #
class TestAcceso:
    def test_anonimo_redirige_a_login(self, db):
        res = Client().get(CHAT_URL)
        assert res.status_code in (302, 403)

    def test_inspector_no_puede_acceder(self, client_inspector):
        res = client_inspector.get(CHAT_URL)
        assert res.status_code == 403

    def test_secretaria_no_puede_acceder(self, db):
        from tests.factories import UsuarioFactory

        user = UsuarioFactory(rol=UsuarioFactory._meta.model.Rol.SECRETARIA)
        user.save()
        c = Client()
        c.force_login(user)
        assert c.get(CHAT_URL).status_code == 403

    def test_estudiante_puede_acceder(self, client_estudiante):
        res = client_estudiante.get(CHAT_URL)
        assert res.status_code == 200

    def test_docente_puede_acceder(self, client_docente):
        res = client_docente.get(CHAT_URL)
        assert res.status_code == 200


# -------------------------------------------------------------------- #
# GET /copilot/chat/ — historial
# -------------------------------------------------------------------- #
class TestGetHistorial:
    def test_retorna_json_con_historial_vacio(self, client_estudiante):
        res = client_estudiante.get(CHAT_URL)
        assert res.status_code == 200
        data = res.json()
        assert "conversacion_id" in data
        assert "mensajes" in data
        assert data["mensajes"] == []

    def test_retorna_mensajes_existentes(self, client_estudiante, estudiante):
        conv = ConversacionCopilot.objects.create(usuario=estudiante)
        MensajeCopilot.objects.create(conversacion=conv, rol="user", contenido="hola")
        MensajeCopilot.objects.create(conversacion=conv, rol="assistant", contenido="buenas")
        res = client_estudiante.get(CHAT_URL)
        data = res.json()
        assert len(data["mensajes"]) == 2
        assert data["mensajes"][0]["rol"] == "user"
        assert data["mensajes"][1]["rol"] == "assistant"


# -------------------------------------------------------------------- #
# Logout resets the conversation (Issue 2 — persistence)
# -------------------------------------------------------------------- #
class TestLogoutCierraConversacion:
    def test_logout_marca_conversacion_activa_como_inactiva(self, client_estudiante, estudiante):
        conv = ConversacionCopilot.objects.create(usuario=estudiante)
        MensajeCopilot.objects.create(conversacion=conv, rol="user", contenido="hola")
        client_estudiante.get(reverse("usuarios:logout"))
        conv.refresh_from_db()
        assert conv.activa is False

    def test_get_historial_tras_logout_arranca_vacio(self, client_estudiante, estudiante):
        conv = ConversacionCopilot.objects.create(usuario=estudiante)
        MensajeCopilot.objects.create(conversacion=conv, rol="user", contenido="hola")
        client_estudiante.get(reverse("usuarios:logout"))
        # Re-login: the previous conversation must no longer surface.
        client_estudiante.force_login(estudiante)
        data = client_estudiante.get(CHAT_URL).json()
        assert data["conversacion_id"] == ""
        assert data["mensajes"] == []


# -------------------------------------------------------------------- #
# POST /copilot/chat/ — enviar mensaje
# -------------------------------------------------------------------- #
class TestPostMensaje:
    def test_mensaje_valido_retorna_200_y_respuesta(self, client_estudiante):
        res = client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "¿Cuál es mi promedio?"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.json()
        assert "respuesta" in data
        assert "timestamp" in data
        # Persistió user + assistant
        assert MensajeCopilot.objects.filter(rol="user").count() == 1
        assert MensajeCopilot.objects.filter(rol="assistant").count() == 1

    def test_body_vacio_retorna_400(self, client_estudiante):
        res = client_estudiante.post(CHAT_URL, data="{}", content_type="application/json")
        assert res.status_code == 400
        assert "error" in res.json()

    def test_sin_json_body_retorna_400(self, client_estudiante):
        res = client_estudiante.post(CHAT_URL, data="not json", content_type="application/json")
        assert res.status_code == 400

    def test_mensaje_demasiado_largo_retorna_400(self, client_estudiante):
        res = client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "x" * 1001}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_mensaje_solo_espacios_retorna_400(self, client_estudiante):
        res = client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "   \n  "}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_rate_limit_retorna_429(self, client_estudiante, monkeypatch):
        """Si el service lanza RateLimitExcedidoError, la vista responde 429."""
        from apps.copilot.domain.exceptions import RateLimitExcedidoError

        original = CopilotAppService

        class RaisingService(original):
            def procesar_mensaje(self, *args, **kwargs):
                raise RateLimitExcedidoError()

        monkeypatch.setattr("apps.copilot.presentation.views.CopilotAppService", RaisingService)
        res = client_estudiante.post(
            CHAT_URL,
            data=json.dumps({"mensaje": "hola"}),
            content_type="application/json",
        )
        assert res.status_code == 429


# -------------------------------------------------------------------- #
# POST /copilot/nueva-conversacion/
# -------------------------------------------------------------------- #
class TestNuevaConversacion:
    def test_cierra_activa_y_crea_nueva(self, client_estudiante, estudiante):
        activa = ConversacionCopilot.objects.create(usuario=estudiante, activa=True)
        res = client_estudiante.post(NUEVA_URL)
        assert res.status_code == 200
        data = res.json()
        assert "conversacion_id" in data
        # La activa debe haber pasado a activa=False
        activa.refresh_from_db()
        assert activa.activa is False
        # Y debe existir una nueva activa
        nueva = ConversacionCopilot.objects.get(pk=data["conversacion_id"])
        assert nueva.activa is True
        assert nueva.pk != activa.pk

    def test_sin_activa_previa_crea_una(self, client_estudiante, estudiante):
        assert not ConversacionCopilot.objects.filter(usuario=estudiante).exists()
        res = client_estudiante.post(NUEVA_URL)
        assert res.status_code == 200
        assert ConversacionCopilot.objects.filter(usuario=estudiante, activa=True).count() == 1

    def test_inspector_no_puede(self, client_inspector):
        res = client_inspector.post(NUEVA_URL)
        assert res.status_code == 403

    def test_anonimo_no_puede(self):
        res = Client().post(NUEVA_URL)
        assert res.status_code in (302, 403)
