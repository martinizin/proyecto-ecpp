"""Tests for session management in CopilotAppService (HU22).

Covers:
- get-or-create active conversation
- 24h timeout (expired sessions are not reused, a new one is created)
- session message cap (50 → SesionLlenaError)
- close-and-start-new conversation
- get history returns ordered messages
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import SesionLlenaError
from apps.copilot.infrastructure.models import ConversacionCopilot
from tests.factories import EstudianteFactory


# -------------------------------------------------------------------- #
# Fixtures
# -------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _subir_rate_limit(monkeypatch):
    """Sube el rate limit para que la lógica de sesión no se confunda
    con la del rate limit por hora."""
    monkeypatch.setattr(CopilotAppService, "MAX_MENSAJES_POR_HORA", 1000)


@pytest.fixture
def fake_openai():
    instance = mock.MagicMock()
    instance.chat_completion.return_value = ("respuesta fake", 42)
    return instance


@pytest.fixture
def service(fake_openai):
    return CopilotAppService(openai_client=fake_openai, academic_data_service=mock.MagicMock())


@pytest.fixture
def estudiante(db):
    user = EstudianteFactory()
    user.save()
    return user


# -------------------------------------------------------------------- #
# obtener_o_crear_conversacion
# -------------------------------------------------------------------- #
class TestObtenerOCrear:
    def test_sin_conversacion_previa_crea_una(self, service, estudiante):
        assert not ConversacionCopilot.objects.filter(usuario=estudiante).exists()
        conv = service.obtener_o_crear_conversacion(estudiante)
        assert conv.usuario == estudiante
        assert conv.activa is True
        assert ConversacionCopilot.objects.filter(usuario=estudiante).count() == 1

    def test_con_sesion_activa_la_reusa(self, service, estudiante):
        primera = service.obtener_o_crear_conversacion(estudiante)
        segunda = service.obtener_o_crear_conversacion(estudiante)
        assert primera.pk == segunda.pk
        assert ConversacionCopilot.objects.filter(usuario=estudiante).count() == 1

    def test_sesion_inactiva_se_ignora_y_crea_nueva(self, service, estudiante):
        vieja = ConversacionCopilot.objects.create(usuario=estudiante, activa=False)
        nueva = service.obtener_o_crear_conversacion(estudiante)
        assert nueva.pk != vieja.pk
        assert nueva.activa is True

    def test_sesion_expirada_se_reemplaza(self, service, estudiante):
        """Una sesión con ultima_actividad > 24h no debe reusarse."""
        vieja = ConversacionCopilot.objects.create(usuario=estudiante, activa=True)
        ConversacionCopilot.objects.filter(pk=vieja.pk).update(
            ultima_actividad=timezone.now() - timedelta(hours=25)
        )
        nueva = service.obtener_o_crear_conversacion(estudiante)
        assert nueva.pk != vieja.pk
        # La vieja sigue activa en DB (no la tocamos al reemplazarla)
        vieja.refresh_from_db()
        assert vieja.activa is True
        assert nueva.activa is True


# -------------------------------------------------------------------- #
# cerrar_conversacion
# -------------------------------------------------------------------- #
class TestCerrarConversacion:
    def test_cierra_activa_y_crea_nueva(self, service, estudiante):
        activa = service.obtener_o_crear_conversacion(estudiante)
        nueva = service.cerrar_conversacion(estudiante)
        activa.refresh_from_db()
        assert activa.activa is False
        assert nueva.pk != activa.pk
        assert nueva.activa is True

    def test_cerrar_sin_activa_crea_nueva(self, service, estudiante):
        nueva = service.cerrar_conversacion(estudiante)
        assert nueva.activa is True
        assert nueva.usuario == estudiante


# -------------------------------------------------------------------- #
# Cap de mensajes por sesión
# -------------------------------------------------------------------- #
class TestCapMensajesPorSesion:
    def test_no_bloquea_bajo_cap(self, service, estudiante, monkeypatch):
        """Si la sesión tiene menos del cap, procesar debe pasar.
        Bajamos el cap a 4 y mandamos 1 mensaje (genera 2 en la sesión)."""
        monkeypatch.setattr(CopilotAppService, "MAX_MENSAJES_POR_SESION", 4)
        # 1 user + 1 assistant = 2 mensajes totales (< 4)
        service.procesar_mensaje(estudiante, "msg 1")

    def test_bloquea_al_exceder_cap(self, service, estudiante, monkeypatch):
        """Cuando la sesión tiene `cap` mensajes, el siguiente dispara SesionLlenaError."""
        monkeypatch.setattr(CopilotAppService, "MAX_MENSAJES_POR_SESION", 4)
        # 2 user + 2 assistant = 4 mensajes (= cap, todavía pasa)
        service.procesar_mensaje(estudiante, "msg 1")
        service.procesar_mensaje(estudiante, "msg 2")
        # El próximo debe disparar
        with pytest.raises(SesionLlenaError) as excinfo:
            service.procesar_mensaje(estudiante, "uno más")
        assert excinfo.value.maximo == 4

    def test_cuenta_user_y_assistant(self, service, estudiante):
        """El cap es de mensajes TOTALES (user + assistant), no solo user."""
        # Cap por defecto = 50. 25 iteraciones = 50 mensajes (25 user + 25 assistant).
        # 26ª iteración debe disparar SesionLlenaError.
        for i in range(25):
            service.procesar_mensaje(estudiante, f"msg {i}")
        with pytest.raises(SesionLlenaError):
            service.procesar_mensaje(estudiante, "uno más")


# -------------------------------------------------------------------- #
# obtener_historial
# -------------------------------------------------------------------- #
class TestObtenerHistorial:
    def test_devuelve_id_y_mensajes_ordenados(self, service, estudiante):
        service.procesar_mensaje(estudiante, "primero")
        service.procesar_mensaje(estudiante, "segundo")
        conv_id, mensajes = service.obtener_historial(estudiante)
        assert conv_id is not None
        # 2 user + 2 assistant = 4
        assert len(mensajes) == 4
        # El orden debe ser cronológico
        roles = [m["rol"] for m in mensajes]
        assert roles == ["user", "assistant", "user", "assistant"]

    def test_no_crea_conversacion_si_no_hay(self, service, estudiante):
        # A GET-style history read must stay idempotent: no active conversation
        # → return empty without spawning a row.
        assert not ConversacionCopilot.objects.filter(usuario=estudiante).exists()
        conv_id, mensajes = service.obtener_historial(estudiante)
        assert conv_id == ""
        assert mensajes == []
        assert not ConversacionCopilot.objects.filter(usuario=estudiante).exists()
