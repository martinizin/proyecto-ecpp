"""
Tests de integración para el endpoint ``GET /reportes/preview/`` (HU27b).

Endpoint de pre-visualización de exportación:
- 3 roles permitidos: docente, inspector, secretaria.
- Rate limit: 20/min/user (independiente del export).
- 400 si ``tipo`` falta o es inválido.
- 200 con shape ``{count, sample_rows, available_periodos, available_paralelos}``.
- 403 si estudiante.

Spec: R12, R13, R14, R15, R17.
"""

import json
from decimal import Decimal

import pytest

from tests.factories import (
    CalificacionFactory,
    DocenteFactory,
    EvaluacionFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    RegistroCalificacionParaleloFactory,
)


pytestmark = pytest.mark.django_db


URL = "/reportes/preview/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _crear_planilla_con_5_estudiantes(periodo=None, docente=None):
    """Crea un paralelo con 5 matrículas y notas registradas."""
    periodo = periodo or PeriodoFactory(nombre="2026-A")
    docente = docente or DocenteFactory()
    paralelo = ParaleloFactory(periodo=periodo, nombre="A", docente=docente)
    RegistroCalificacionParaleloFactory(paralelo=paralelo)
    evs = []
    for tipo, peso in [
        ("parcial1", Decimal("30.00")),
        ("parcial2_10h", Decimal("30.00")),
        ("examen_final", Decimal("40.00")),
    ]:
        evs.append(EvaluacionFactory(paralelo=paralelo, tipo=tipo, peso=peso))
    for _ in range(5):
        matricula = MatriculaFactory(paralelo=paralelo)
        for ev in evs:
            CalificacionFactory(
                evaluacion=ev,
                estudiante=matricula.estudiante,
                nota=Decimal("15.00"),
            )
    return periodo, paralelo


def _crear_planilla_para_docente(docente, periodo=None):
    """Crea un paralelo asignado al ``docente`` dado (no uno nuevo)."""
    periodo = periodo or PeriodoFactory(nombre="2026-A")
    paralelo = ParaleloFactory(periodo=periodo, nombre="A", docente=docente)
    RegistroCalificacionParaleloFactory(paralelo=paralelo)
    evs = []
    for tipo, peso in [
        ("parcial1", Decimal("30.00")),
        ("parcial2_10h", Decimal("30.00")),
        ("examen_final", Decimal("40.00")),
    ]:
        evs.append(EvaluacionFactory(paralelo=paralelo, tipo=tipo, peso=peso))
    for _ in range(5):
        matricula = MatriculaFactory(paralelo=paralelo)
        for ev in evs:
            CalificacionFactory(
                evaluacion=ev,
                estudiante=matricula.estudiante,
                nota=Decimal("15.00"),
            )
    return periodo, paralelo


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestPreviewHappyPath:
    """El endpoint retorna la estructura JSON correcta para los 3 roles."""

    def test_preview_calificaciones_docente_returns_200_with_count_and_sample(
        self, docente_client
    ):
        """Docente: GET con tipo=calificaciones retorna 200, count=5, sample_rows=3."""
        periodo, paralelo = _crear_planilla_con_5_estudiantes()

        response = docente_client.get(
            URL, {"tipo": "calificaciones", "periodo": periodo.id, "paralelo": paralelo.id}
        )
        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["count"] == 5
        assert len(body["sample_rows"]) == 3
        # Filas tienen las claves esperadas
        fila = body["sample_rows"][0]
        assert "cedula" in fila
        assert "nombres" in fila
        assert "promedio" in fila
        assert "estado" in fila

    def test_preview_asistencia_returns_count_and_sample(self, docente_client):
        """Docente: GET con tipo=asistencia retorna 200 con shape correcto."""
        from datetime import date
        from tests.factories import AsistenciaFactory
        from apps.asistencia.infrastructure.models import Asistencia

        periodo = PeriodoFactory(nombre="2026-A")
        paralelo = ParaleloFactory(periodo=periodo, nombre="A")
        for i in range(5):
            matricula = MatriculaFactory(paralelo=paralelo)
            for d in range(1, 11):
                AsistenciaFactory(
                    estudiante=matricula.estudiante,
                    paralelo=paralelo,
                    fecha=date(2026, 4, d),
                    estado=Asistencia.Estado.PRESENTE,
                )

        response = docente_client.get(
            URL, {"tipo": "asistencia", "periodo": periodo.id, "paralelo": paralelo.id}
        )
        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["count"] == 5
        assert len(body["sample_rows"]) == 3
        fila = body["sample_rows"][0]
        assert "cedula" in fila
        assert "nombres" in fila
        assert "porcentaje_asistencia" in fila
        assert "estado" in fila

    def test_preview_response_has_available_periodos_and_paralelos(self, docente, docente_client):
        """El body incluye ``available_periodos`` y ``available_paralelos``."""
        periodo, paralelo = _crear_planilla_para_docente(docente)

        response = docente_client.get(
            URL, {"tipo": "calificaciones", "periodo": periodo.id, "paralelo": paralelo.id}
        )
        body = json.loads(response.content)
        assert "available_periodos" in body
        assert "available_paralelos" in body
        assert isinstance(body["available_periodos"], list)
        assert isinstance(body["available_paralelos"], list)
        # El periodo actual está en available_periodos
        assert any(p["id"] == periodo.id for p in body["available_periodos"])

    def test_preview_content_type_is_json(self, docente_client):
        """El Content-Type es application/json."""
        periodo, _ = _crear_planilla_con_5_estudiantes()
        response = docente_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response["Content-Type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------


class TestPreviewEmptyResult:
    """Si no hay matrículas, el response es 200 con ``count=0`` y ``sample_rows=[]``."""

    def test_preview_empty_filter_returns_200_count_zero(self, docente_client):
        """Periodo sin paralelos → 200 con count=0, sample_rows=[]."""
        periodo = PeriodoFactory(nombre="2026-A")
        response = docente_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["count"] == 0
        assert body["sample_rows"] == []


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------


class TestPreviewValidation:
    """Validación de query params."""

    def test_preview_tipo_invalido_retorna_400(self, docente_client):
        """``tipo`` no permitido → 400 con body de error."""
        periodo = PeriodoFactory(nombre="2026-A")
        response = docente_client.get(URL, {"tipo": "foo", "periodo": periodo.id})
        assert response.status_code == 400
        body = json.loads(response.content)
        assert body["error"] == "invalid_tipo"
        assert body["allowed"] == ["calificaciones", "asistencia"]

    def test_preview_tipo_faltante_retorna_400(self, docente_client):
        """``tipo`` ausente → 400 con body de error."""
        periodo = PeriodoFactory(nombre="2026-A")
        response = docente_client.get(URL, {"periodo": periodo.id})
        assert response.status_code == 400
        body = json.loads(response.content)
        assert body["error"] == "invalid_tipo"

    def test_preview_400_content_type_is_json(self, docente_client):
        """El 400 retorna JSON (no texto plano)."""
        periodo = PeriodoFactory(nombre="2026-A")
        response = docente_client.get(URL, {"periodo": periodo.id})
        assert response["Content-Type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Role gate
# ---------------------------------------------------------------------------


class TestPreviewRoleGate:
    """El endpoint solo permite los 3 roles definidos."""

    def test_preview_docente_200(self, docente_client):
        periodo, _ = _crear_planilla_con_5_estudiantes()
        response = docente_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code == 200

    def test_preview_inspector_200(self, inspector_client):
        periodo, _ = _crear_planilla_con_5_estudiantes()
        response = inspector_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code == 200

    def test_preview_secretaria_200(self, secretaria_client):
        periodo, _ = _crear_planilla_con_5_estudiantes()
        response = secretaria_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code == 200

    def test_preview_estudiante_403(self, estudiante_client):
        periodo, _ = _crear_planilla_con_5_estudiantes()
        response = estudiante_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code == 403

    def test_preview_anonymous_redirects_to_login(self, client):
        periodo, _ = _crear_planilla_con_5_estudiantes()
        response = client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code in (302, 403)


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------


class TestPreviewRateLimit:
    """El endpoint aplica 20/min/user (independiente del export)."""

    def test_preview_20_requests_succeed(self, docente_client):
        """Las primeras 20 requests retornan 200."""
        periodo, _ = _crear_planilla_con_5_estudiantes()
        for _ in range(20):
            response = docente_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
            assert response.status_code == 200

    def test_preview_21st_request_returns_429_json(self, docente_client):
        """La 21ª retorna 429 con JSON shape."""
        periodo, _ = _crear_planilla_con_5_estudiantes()
        for _ in range(20):
            docente_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})

        response = docente_client.get(URL, {"tipo": "calificaciones", "periodo": periodo.id})
        assert response.status_code == 429
        body = json.loads(response.content)
        assert body == {"error": "rate_limit", "retry_after_seconds": 60}
        assert response["Content-Type"].startswith("application/json")
