"""Tests for rate limiting in CopilotAppService (HU22).

The copilot must cap the number of user messages per hour to prevent
abuse. Threshold is `MAX_MENSAJES_POR_HORA = 30`. We patch
`OpenAIClient.chat_completion` so the test never hits the real API.
"""

from unittest import mock

import pytest

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import RateLimitExcedidoError
from apps.copilot.infrastructure.models import ConversacionCopilot, MensajeCopilot
from tests.factories import EstudianteFactory


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _subir_tope_sesion(monkeypatch):
    """Sube el límite por sesión a 1000 para que el rate limit por hora
    sea lo único que se dispare en estos tests (si no, 30 user+30 assistant
    pasaría el cap de 50 y se confundiría con el error de sesión)."""
    monkeypatch.setattr(CopilotAppService, "MAX_MENSAJES_POR_SESION", 1000)


@pytest.fixture
def fake_openai(monkeypatch):
    """Replace openai_client with a MagicMock that returns a deterministic reply."""
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
# Rate limit por hora
# -------------------------------------------------------------------- #
class TestRateLimitePorHora:
    def test_no_bloquea_bajo_limite(self, service, estudiante):
        """Hasta 30 mensajes por hora: no debe lanzar RateLimitExcedidoError."""
        for i in range(CopilotAppService.MAX_MENSAJES_POR_HORA):
            service.procesar_mensaje(estudiante, f"consulta {i}")
        # Si llegamos aquí, no hubo excepción

    def test_bloquea_al_exceder_limite(self, service, estudiante):
        """El mensaje número 31 debe lanzar RateLimitExcedidoError."""
        for i in range(CopilotAppService.MAX_MENSAJES_POR_HORA):
            service.procesar_mensaje(estudiante, f"consulta {i}")
        with pytest.raises(RateLimitExcedidoError) as excinfo:
            service.procesar_mensaje(estudiante, "una más, no debería pasar")
        assert excinfo.value.limite == CopilotAppService.MAX_MENSAJES_POR_HORA

    def test_no_persiste_mensaje_cuando_excede(self, service, estudiante):
        """Si el rate limit bloquea, no se debe persistir el mensaje del usuario."""
        for i in range(CopilotAppService.MAX_MENSAJES_POR_HORA):
            service.procesar_mensaje(estudiante, f"consulta {i}")
        with pytest.raises(RateLimitExcedidoError):
            service.procesar_mensaje(estudiante, "no debe guardarse")
        # El conteo de mensajes del usuario debe seguir en el límite
        count_user = MensajeCopilot.objects.filter(
            conversacion__usuario=estudiante, rol=MensajeCopilot.Rol.USER
        ).count()
        assert count_user == CopilotAppService.MAX_MENSAJES_POR_HORA


# -------------------------------------------------------------------- #
# Rate limit aislado por usuario
# -------------------------------------------------------------------- #
class TestRateLimitePorUsuario:
    def test_otro_usuario_no_se_ve_afectado(self, service, db):
        """El rate limit es por usuario: si A se bloquea, B puede seguir."""
        from tests.factories import EstudianteFactory

        user_a = EstudianteFactory(username="alice", cedula="1700000001")
        user_a.save()
        user_b = EstudianteFactory(username="bob", cedula="1700000002")
        user_b.save()

        # Agotar a user_a
        for i in range(CopilotAppService.MAX_MENSAJES_POR_HORA):
            service.procesar_mensaje(user_a, f"a-{i}")
        with pytest.raises(RateLimitExcedidoError):
            service.procesar_mensaje(user_a, "uno más")

        # user_b puede mandar tranquilo
        for i in range(5):
            service.procesar_mensaje(user_b, f"b-{i}")


# -------------------------------------------------------------------- #
# Rate limit considera ventana de 1h, no historial total
# -------------------------------------------------------------------- #
class TestVentanaDeUnaHora:
    def test_mensajes_de_hace_mas_de_una_hora_no_cuentan(self, service, estudiante):
        """Mensajes antiguos (>1h) no deben contar para el rate limit."""
        from datetime import timedelta

        from django.utils import timezone

        # Sembrar 30 mensajes viejos (hace 2 horas)
        conv = ConversacionCopilot.objects.create(usuario=estudiante)
        for i in range(CopilotAppService.MAX_MENSAJES_POR_HORA):
            msg = MensajeCopilot.objects.create(
                conversacion=conv,
                rol=MensajeCopilot.Rol.USER,
                contenido=f"viejo {i}",
            )
            # Forzar timestamp al pasado
            MensajeCopilot.objects.filter(pk=msg.pk).update(
                timestamp=timezone.now() - timedelta(hours=2)
            )

        # Un mensaje nuevo debe pasar OK porque los viejos ya expiraron
        service.procesar_mensaje(estudiante, "mensaje nuevo")
