"""
Tests para el contrato 429 → JSON de los endpoints de exportación de reportes (HU27b).

Sustituye al body ``text/plain`` previo por un JSON estructurado que el
componente Alpine ``exportFlow()`` puede consumir para mostrar un toast
con countdown.

Contrato (R18 del spec reportes-ux-hub):
- HTTP 429
- ``Content-Type: application/json``
- body: ``{"error": "rate_limit", "retry_after_seconds": 60}``
- El límite 10/min de ``ExportacionRateLimiter`` (R3 de reportes-exportacion)
  se mantiene sin cambios.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from tests.factories import ParaleloFactory, PeriodoFactory


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prep_docente_cache_at_limit(limit: int = 10) -> None:
    """Pre-popula el cache del docente a ``limit`` para que la 11ª request sea 429."""
    Usuario = get_user_model()
    user = Usuario.objects.filter(rol="docente").order_by("-id").first()
    assert user is not None
    bucket = timezone.now().strftime("%Y%m%d%H%M")
    cache.set(f"export_rate_{user.id}_{bucket}", limit, timeout=60)


# ---------------------------------------------------------------------------
# Calificaciones
# ---------------------------------------------------------------------------


class TestCalificaciones429Json:
    """``ExportarCalificacionesView`` retorna JSON 429 cuando se excede el límite."""

    def setup_method(self):
        self.periodo = PeriodoFactory(nombre="2026-A")
        ParaleloFactory(periodo=self.periodo, nombre="A")
        self.url = reverse("reportes:exportar_calificaciones")

    def test_429_status_code(self, docente_client):
        """La 11ª request retorna HTTP 429."""
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        assert response.status_code == 429

    def test_429_content_type_is_json(self, docente_client):
        """El ``Content-Type`` es ``application/json`` (no ``text/plain``)."""
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        assert response["Content-Type"].startswith("application/json")

    def test_429_body_has_rate_limit_error_key(self, docente_client):
        """El body parsea a un dict con ``error == "rate_limit"``."""
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        body = json.loads(response.content)
        assert body == {"error": "rate_limit", "retry_after_seconds": 60}

    def test_429_body_has_retry_after_seconds_60(self, docente_client):
        """El campo ``retry_after_seconds`` es exactamente 60."""
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        body = json.loads(response.content)
        assert body["retry_after_seconds"] == 60

    def test_429_does_not_contain_spanish_text_body(self, docente_client):
        """El body NO contiene el mensaje en español previo (``Límite``/``limite``)."""
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        body_text = response.content.decode("utf-8")
        assert "Límite" not in body_text
        assert "limite" not in body_text.lower()


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------


class TestAsistencia429Json:
    """``ExportarAsistenciaView`` retorna JSON 429 cuando se excede el límite."""

    def setup_method(self):
        self.periodo = PeriodoFactory(nombre="2026-A")
        ParaleloFactory(periodo=self.periodo, nombre="A")
        self.url = reverse("reportes:exportar_asistencia")

    def test_429_status_code(self, docente_client):
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        assert response.status_code == 429

    def test_429_content_type_is_json(self, docente_client):
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        assert response["Content-Type"].startswith("application/json")

    def test_429_body_shape(self, docente_client):
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        body = json.loads(response.content)
        assert body == {"error": "rate_limit", "retry_after_seconds": 60}

    def test_429_does_not_contain_spanish_text_body(self, docente_client):
        _prep_docente_cache_at_limit()
        response = docente_client.get(self.url, {"periodo": self.periodo.id, "formato": "excel"})
        body_text = response.content.decode("utf-8")
        assert "Límite" not in body_text
        assert "limite" not in body_text.lower()
