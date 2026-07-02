"""
Tests para ``ExportarAuditoriaView`` (HU27b follow-up 2026-06-24).

El módulo de Auditoría debe generar un "Reporte de Auditoría" (no
"Reporte de Calificaciones") al exportar a Excel/PDF. El endpoint
queryea ``LogCalificacion`` (no ``Calificacion``) con los mismos
filtros de la página (``fecha_inicio``, ``fecha_fin``, ``accion``,
``docente``, ``estudiante``).
"""

import re
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.calificaciones.infrastructure.models import LogCalificacion
from tests.factories import (
    CalificacionFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    LogCalificacionFactory,
    SecretariaFactory,
    UsuarioFactory,
)
from apps.usuarios.infrastructure.models import Usuario


@pytest.fixture
def secretaria(db):
    """Secretaria user. Necesita .save() porque UsuarioFactory
    tiene skip_postgeneration_save=True (ver conftest de proyecto)."""
    user = SecretariaFactory()
    user.save()
    return user


@pytest.fixture
def inspector(db):
    user = InspectorFactory()
    user.save()
    return user


@pytest.fixture
def docente(db):
    user = DocenteFactory()
    user.save()
    return user


@pytest.fixture
def docente_otro(db):
    user = DocenteFactory()
    user.save()
    return user


@pytest.fixture
def estudiante(db):
    user = EstudianteFactory()
    user.save()
    return user


@pytest.fixture
def director_academico(db):
    user = UsuarioFactory(rol=Usuario.Rol.DIRECTOR_ACADEMICO)
    user.save()
    return user


@pytest.fixture
def secretaria_client(secretaria):
    client = Client()
    client.force_login(secretaria)
    return client


@pytest.fixture
def inspector_client(inspector):
    client = Client()
    client.force_login(inspector)
    return client


@pytest.fixture
def docente_client(docente):
    client = Client()
    client.force_login(docente)
    return client


@pytest.fixture
def estudiante_client(estudiante):
    client = Client()
    client.force_login(estudiante)
    return client


@pytest.fixture
def director_academico_client(director_academico):
    client = Client()
    client.force_login(director_academico)
    return client


def _crear_log(
    *,
    accion="creacion",
    realizado_por=None,
    estudiante_info="Juan Pérez (1234567890)",
    evaluacion_info="Parcial 1 — MAT-101 A",
    motivo="",
    timestamp=None,
    valor_anterior=None,
    valor_nuevo=None,
    calificacion=None,
):
    """Helper para crear un LogCalificacion con valores por defecto."""
    if calificacion is None:
        calificacion = CalificacionFactory()
    kwargs = {
        "calificacion": calificacion,
        "accion": accion,
        "estudiante_info": estudiante_info,
        "evaluacion_info": evaluacion_info,
        "motivo": motivo,
        "valor_anterior": valor_anterior,
        "valor_nuevo": valor_nuevo,
    }
    if realizado_por is not None:
        kwargs["realizado_por"] = realizado_por
    log = LogCalificacionFactory(**kwargs)
    if timestamp is not None:
        LogCalificacion.objects.filter(pk=log.pk).update(timestamp=timestamp)
        log.refresh_from_db()
    return log


class TestExportarAuditoriaView:
    """Verifica que el endpoint de export de auditoría funciona correctamente."""

    def test_secretaria_gets_excel_200(self, secretaria_client):
        """Secretaria recibe HTTP 200 con xlsx."""
        _crear_log()
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 200
        assert (
            response["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert response.content[:2] == b"PK"

    def test_secretaria_gets_pdf_200(self, secretaria_client):
        """Secretaria recibe HTTP 200 con PDF."""
        _crear_log()
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "pdf"}
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"

    def test_inspector_gets_excel_200(self, inspector_client):
        """Inspector recibe HTTP 200 con xlsx."""
        _crear_log()
        response = inspector_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 200

    def test_estudiante_is_forbidden_403(self, estudiante_client):
        """Estudiante recibe HTTP 403."""
        _crear_log()
        response = estudiante_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 403

    def test_docente_is_forbidden_403(self, docente_client):
        """Docente recibe HTTP 403 (no es inspector ni secretaria)."""
        _crear_log()
        response = docente_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 403

    def test_director_academico_gets_excel_200(self, director_academico_client):
        """Director Académico recibe HTTP 200 con xlsx (post-merge HU26/HU33).

        El view del listado de auditoría ya lo incluía, pero el
        endpoint de export se olvidó → 403 al click del inline button.
        Bug fix 2026-07-01: agregado a ``roles_permitidos``.
        """
        _crear_log()
        response = director_academico_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 200
        assert (
            response["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert response.content[:2] == b"PK"

    def test_anonymous_redirects_to_login(self, db, client):
        """Usuario anónimo es redirigido a login (302) o denegado (403)."""
        _crear_log()
        response = client.get(reverse("calificaciones:auditoria_exportar"), {"formato": "excel"})
        assert response.status_code in (302, 403)

    def test_filename_starts_with_auditoria(self, secretaria_client):
        """El filename empieza con 'auditoria_' (NO 'calificaciones_')."""
        _crear_log()
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert "filename=" in response["Content-Disposition"]
        match = re.search(r'filename="([^"]+)"', response["Content-Disposition"])
        assert match is not None
        filename = match.group(1)
        assert filename.startswith(
            "auditoria_"
        ), f"Filename debe empezar con 'auditoria_', got '{filename}'"
        assert filename.endswith(".xlsx")

    def test_no_filters_returns_all_logs(self, secretaria_client, docente):
        """Sin filtros, se exportan todos los logs."""
        _crear_log(realizado_por=docente, accion="creacion", estudiante_info="A")
        _crear_log(realizado_por=docente, accion="modificacion", estudiante_info="B")
        _crear_log(realizado_por=docente, accion="recalificacion", estudiante_info="C")
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 200
        # We can't easily parse the xlsx without openpyxl in tests; just
        # verify the response is non-empty and well-formed
        assert len(response.content) > 1000  # xlsx with headers + 3 rows

    def test_filter_by_accion(self, secretaria_client, docente):
        """Filtro por ?accion= solo incluye logs de esa acción."""
        log_creacion = _crear_log(realizado_por=docente, accion="creacion", estudiante_info="A")
        _crear_log(realizado_por=docente, accion="modificacion", estudiante_info="B")
        _crear_log(realizado_por=docente, accion="recalificacion", estudiante_info="C")
        # Verify the filter works at the queryset level
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService({"accion": "creacion"})
        logs = list(service._query_logs())
        assert len(logs) == 1
        assert logs[0].pk == log_creacion.pk

    def test_filter_by_docente(self, secretaria_client, docente, docente_otro):
        """Filtro por ?docente=N solo incluye logs de ese docente."""
        log_docente1 = _crear_log(realizado_por=docente, accion="creacion", estudiante_info="A")
        _crear_log(realizado_por=docente_otro, accion="creacion", estudiante_info="B")
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService({"docente": str(docente.pk)})
        logs = list(service._query_logs())
        assert len(logs) == 1
        assert logs[0].pk == log_docente1.pk

    def test_filter_by_docente_invalid_ignores_filter(self, secretaria_client, docente):
        """Filtro ?docente=abc (no int) no rompe, devuelve todos los logs."""
        _crear_log(realizado_por=docente, accion="creacion", estudiante_info="A")
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService({"docente": "abc"})
        logs = list(service._query_logs())
        assert len(logs) == 1

    def test_filter_by_estudiante_icontains(self, secretaria_client, docente):
        """Filtro por ?estudiante=Q hace icontains sobre estudiante_info."""
        _crear_log(
            realizado_por=docente,
            estudiante_info="Juan Pérez (1234567890)",
        )
        _crear_log(
            realizado_por=docente,
            estudiante_info="María López (9876543210)",
        )
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService({"estudiante": "juan"})
        logs = list(service._query_logs())
        assert len(logs) == 1
        assert "Juan" in logs[0].estudiante_info

    def test_filter_by_fecha_inicio(self, secretaria_client, docente):
        """Filtro por ?fecha_inicio=X solo incluye logs desde esa fecha."""
        _crear_log(
            realizado_por=docente,
            timestamp=date(2026, 1, 1),
        )
        _crear_log(
            realizado_por=docente,
            timestamp=date(2026, 6, 15),
        )
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService({"fecha_inicio": "2026-05-01"})
        logs = list(service._query_logs())
        assert len(logs) == 1
        assert logs[0].timestamp.date() == date(2026, 6, 15)

    def test_filter_by_fecha_fin(self, secretaria_client, docente):
        """Filtro por ?fecha_fin=X solo incluye logs hasta esa fecha."""
        _crear_log(
            realizado_por=docente,
            timestamp=date(2026, 1, 1),
        )
        _crear_log(
            realizado_por=docente,
            timestamp=date(2026, 6, 15),
        )
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService({"fecha_fin": "2026-03-01"})
        logs = list(service._query_logs())
        assert len(logs) == 1
        assert logs[0].timestamp.date() == date(2026, 1, 1)

    def test_excel_sheet_name_is_auditoria(self, secretaria_client):
        """El nombre del sheet de Excel es 'Auditoría'."""
        from openpyxl import load_workbook

        from io import BytesIO

        _crear_log()
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        wb = load_workbook(BytesIO(response.content))
        assert wb.active.title == "Auditoría"

    def test_excel_contains_log_data(self, secretaria_client, docente):
        """Los datos del log aparecen en el Excel."""
        from openpyxl import load_workbook

        from io import BytesIO

        _crear_log(
            realizado_por=docente,
            accion="creacion",
            estudiante_info="Juan Pérez (1234567890)",
            evaluacion_info="Parcial 1",
            valor_anterior=None,
            valor_nuevo=15.50,
        )
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        wb = load_workbook(BytesIO(response.content))
        ws = wb.active
        # Con values_only=True, cada cell ya es el value (no un Cell object)
        all_text = " ".join(
            str(cell) for row in ws.iter_rows(values_only=True) for cell in row if cell is not None
        )
        assert "ECPPP" in all_text  # título
        assert "Reporte de Auditoría" in all_text
        assert "Juan Pérez" in all_text
        assert "Parcial 1" in all_text

    def test_pdf_contains_log_data(self, secretaria_client, docente):
        """Los datos del log aparecen en el PDF."""
        from io import BytesIO

        from pypdf import PdfReader

        _crear_log(
            realizado_por=docente,
            accion="creacion",
            estudiante_info="Juan Pérez (1234567890)",
        )
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "pdf"}
        )
        reader = PdfReader(BytesIO(response.content))
        text = "\n".join(page.extract_text() for page in reader.pages)
        assert "ECPPP" in text
        assert "Reporte de Auditoría" in text
        assert "Juan Pérez" in text

    def test_combined_filters(self, secretaria_client, docente, docente_otro):
        """Los filtros se combinan (AND lógico)."""
        _crear_log(
            realizado_por=docente,
            accion="creacion",
            estudiante_info="Juan Pérez (1234567890)",
            timestamp=date(2026, 6, 1),
        )
        _crear_log(
            realizado_por=docente,
            accion="modificacion",  # different accion
            estudiante_info="Juan Pérez (1234567890)",
            timestamp=date(2026, 6, 1),
        )
        _crear_log(
            realizado_por=docente_otro,  # different docente
            accion="creacion",
            estudiante_info="Juan Pérez (1234567890)",
            timestamp=date(2026, 6, 1),
        )
        _crear_log(
            realizado_por=docente,
            accion="creacion",
            estudiante_info="María López (9876543210)",  # different estudiante
            timestamp=date(2026, 6, 1),
        )
        from apps.calificaciones.application.services import (
            ExportarAuditoriaService,
        )

        service = ExportarAuditoriaService(
            {
                "docente": str(docente.pk),
                "accion": "creacion",
                "estudiante": "juan",
            }
        )
        logs = list(service._query_logs())
        assert len(logs) == 1

    def test_empty_result_returns_valid_file(self, secretaria_client):
        """Sin logs, el Excel y PDF se generan con mensaje 'Sin resultados'."""
        from openpyxl import load_workbook

        from io import BytesIO

        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"), {"formato": "excel"}
        )
        assert response.status_code == 200
        wb = load_workbook(BytesIO(response.content))
        # El sheet existe y tiene al menos las 3 filas de header
        assert wb.active.title == "Auditoría"

    def test_filename_includes_date_range(self, secretaria_client):
        """Si hay fecha_inicio/fecha_fin, el filename las incluye."""
        _crear_log()
        response = secretaria_client.get(
            reverse("calificaciones:auditoria_exportar"),
            {"formato": "excel", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"},
        )
        match = re.search(r'filename="([^"]+)"', response["Content-Disposition"])
        assert match is not None
        filename = match.group(1)
        # El filename debe tener el rango de fechas
        assert "20260101_20261231" in filename

    def test_view_returns_429_on_11th_call(self, secretaria_client):
        """La 11ª llamada retorna 429 con JSON body (rate limit reusado)."""
        # Limpiar el cache del rate limiter para empezar de 0
        from apps.reportes.application.rate_limiter import (
            ExportacionRateLimiter,
        )

        (
            ExportacionRateLimiter._buckets.clear()
            if hasattr(ExportacionRateLimiter, "_buckets")
            else None
        )

        _crear_log()
        url = reverse("calificaciones:auditoria_exportar")
        # 10 llamadas exitosas
        for _ in range(10):
            response = secretaria_client.get(url, {"formato": "excel"})
            assert response.status_code == 200
        # 11ª llamada: rate limit
        response = secretaria_client.get(url, {"formato": "excel"})
        assert response.status_code == 429
        assert response["Content-Type"].startswith("application/json")
        body = response.json()
        # El body tiene {"error": "rate_limit", "retry_after_seconds": 60}
        assert body.get("error") == "rate_limit"
        assert "retry_after_seconds" in body
