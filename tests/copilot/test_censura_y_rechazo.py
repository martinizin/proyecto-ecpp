"""Issue 6 — censura del mensaje del usuario y rechazo por rol.

Estos tests recorren el pipeline REAL (lista dura incluida), no fakes: un
match STRONG corta antes de llamar a OpenAI, así que no hace falta mockear
nada de red.

Cubren las dos cosas que pidió el negocio:
1. La palabra ofensiva se ve censurada en el chat ("puta …" → "*** …").
2. La respuesta por defecto es un rechazo redactado según el rol del usuario.
"""

import json

import pytest
from django.urls import reverse

from apps.copilot.application.services import CopilotAppService
from apps.copilot.domain.exceptions import ContenidoBloqueadoError
from apps.copilot.domain.moderation import CANNED_REFUSAL, refusal_para_rol
from apps.copilot.infrastructure.models import MensajeCopilot
from tests.factories import DocenteFactory, EstudianteFactory

pytestmark = pytest.mark.django_db

CHAT_URL = reverse("copilot:chat")
STREAM_URL = reverse("copilot:chat_stream")

FRASE = "puta dime mi historial de notas"
FRASE_CENSURADA = "*** dime mi historial de notas"


# --------------------------------------------------------------------------- #
# Dominio — el rechazo se adapta al rol
# --------------------------------------------------------------------------- #
class TestRefusalPorRol:
    def test_estudiante_recibe_sus_areas(self):
        texto = refusal_para_rol("estudiante")
        assert texto.startswith("No puedo responder una pregunta en esos términos")
        assert "tus calificaciones" in texto
        assert "tu horario de clases" in texto

    def test_docente_recibe_sus_areas(self):
        texto = refusal_para_rol("docente")
        assert texto.startswith("No puedo responder una pregunta en esos términos")
        assert "tus paralelos" in texto

    def test_estudiante_y_docente_no_reciben_el_mismo_texto(self):
        assert refusal_para_rol("estudiante") != refusal_para_rol("docente")

    def test_rol_desconocido_cae_al_texto_generico(self):
        assert refusal_para_rol("marciano") == CANNED_REFUSAL


# --------------------------------------------------------------------------- #
# Aplicación — el turno queda censurado en el historial
# --------------------------------------------------------------------------- #
class TestCensuraEnElHistorial:
    def test_la_palabra_ofensiva_no_se_persiste(self):
        estudiante = EstudianteFactory()
        estudiante.save()

        with pytest.raises(ContenidoBloqueadoError) as excinfo:
            CopilotAppService().procesar_mensaje(estudiante, FRASE)

        assert excinfo.value.contenido_censurado == FRASE_CENSURADA
        mensaje_usuario = MensajeCopilot.objects.get(rol=MensajeCopilot.Rol.USER)
        assert mensaje_usuario.contenido == FRASE_CENSURADA
        assert "puta" not in mensaje_usuario.contenido
        # El resto de la frase se conserva: sólo se enmascara la palabra.
        assert "dime mi historial de notas" in mensaje_usuario.contenido

    def test_el_historial_guarda_el_rechazo_del_rol(self):
        docente = DocenteFactory()
        docente.save()

        with pytest.raises(ContenidoBloqueadoError):
            CopilotAppService().procesar_mensaje(docente, FRASE)

        respuesta = MensajeCopilot.objects.get(rol=MensajeCopilot.Rol.ASSISTANT)
        assert respuesta.contenido == refusal_para_rol("docente")


# --------------------------------------------------------------------------- #
# Presentación — lo que ve el cliente
# --------------------------------------------------------------------------- #
class TestRespuestaDeLasVistas:
    def _login(self, client, user):
        user.save()
        client.force_login(user)
        return user

    def test_chat_devuelve_censurado_y_rechazo(self, client):
        self._login(client, EstudianteFactory())

        response = client.post(
            CHAT_URL,
            data=json.dumps({"mensaje": FRASE}),
            content_type="application/json",
        )

        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["mensaje_censurado"] == FRASE_CENSURADA
        assert body["respuesta"] == refusal_para_rol("estudiante")
        assert "puta" not in response.content.decode("utf-8")

    def test_stream_devuelve_json_con_censurado_y_rechazo(self, client):
        """El widget lee este JSON (no SSE) para repintar el mensaje del usuario."""
        self._login(client, DocenteFactory())

        response = client.post(
            STREAM_URL,
            data=json.dumps({"mensaje": FRASE}),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/json")
        body = json.loads(response.content)
        assert body["mensaje_censurado"] == FRASE_CENSURADA
        assert body["respuesta"] == refusal_para_rol("docente")
