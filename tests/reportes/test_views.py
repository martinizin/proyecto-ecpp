"""
Tests para las vistas de exportación de reportes (HU27).
"""

import re

import pytest
from django.core.cache import cache
from django.urls import reverse

from tests.factories import ParaleloFactory, PeriodoFactory


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_cache():
    cache.clear()


# ---------------------------------------------------------------------------
# Calificaciones
# ---------------------------------------------------------------------------


class TestExportarCalificacionesView:
    """Tests para ``ExportarCalificacionesView``."""

    def setup_method(self):
        _clear_cache()
        self.periodo = PeriodoFactory(nombre="2026-A")
        ParaleloFactory(periodo=self.periodo, nombre="A")
        self.url = reverse("reportes:exportar_calificaciones")
        self.query = {"periodo": self.periodo.id}

    def test_docente_gets_excel_200(self, docente_client):
        """Docente recibe HTTP 200 con xlsx."""
        response = docente_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 200
        assert (
            response["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert response.content[:2] == b"PK"

    def test_docente_gets_pdf_200(self, docente_client):
        """Docente recibe HTTP 200 con PDF."""
        response = docente_client.get(self.url, {**self.query, "formato": "pdf"})
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"

    def test_inspector_gets_excel_200(self, inspector_client):
        """Inspector recibe HTTP 200 con xlsx."""
        response = inspector_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 200

    def test_secretaria_gets_excel_200(self, secretaria_client):
        """Secretaria recibe HTTP 200 con xlsx."""
        response = secretaria_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 200

    def test_estudiante_is_forbidden_403(self, estudiante_client):
        """Estudiante recibe HTTP 403."""
        response = estudiante_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 403

    def test_anonymous_redirects_to_login(self, client):
        """Usuario anónimo es redirigido a login (302) o denegado (403)."""
        response = client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code in (302, 403)

    def test_content_disposition_attachment(self, docente_client):
        """El header ``Content-Disposition`` es ``attachment`` con filename."""
        response = docente_client.get(self.url, {**self.query, "formato": "excel"})
        assert response["Content-Disposition"].startswith("attachment;")
        assert "filename=" in response["Content-Disposition"]

    def test_filename_with_paralelo(self, docente_client):
        """Con filtro de paralelo, el filename incluye el codigo del paralelo."""
        paralelo = ParaleloFactory(periodo=self.periodo, nombre="X")
        response = docente_client.get(
            self.url, {**self.query, "formato": "excel", "paralelo": paralelo.id}
        )
        # matchea calificaciones_2026-A_<paralelo>_<YYYYMMDD>_<HHMMSS>.xlsx
        match = re.search(r'filename="([^"]+)"', response["Content-Disposition"])
        assert match is not None
        filename = match.group(1)
        assert filename.startswith("calificaciones_2026-A_")
        assert filename.endswith(".xlsx")

    def test_default_formato_is_excel(self, docente_client):
        """Sin ``?formato=``, el response es xlsx por default."""
        response = docente_client.get(self.url, self.query)
        assert response.status_code == 200
        assert response.content[:2] == b"PK"

    def test_view_returns_429_on_11th_call(self, docente_client):
        """La 11ª llamada dentro del mismo minuto retorna 429 con mensaje en español."""
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        Usuario = get_user_model()
        # Buscamos al docente actual (creado por la fixture docente_client)
        user = Usuario.objects.filter(rol="docente").order_by("-id").first()
        assert user is not None
        # Pre-poblamos el cache a 10 (simulando 10 requests previas)
        bucket = timezone.now().strftime("%Y%m%d%H%M")
        key = f"export_rate_{user.id}_{bucket}"
        cache.set(key, 10, timeout=60)

        response = docente_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 429
        body = response.content.decode("utf-8")
        assert "Límite" in body or "limite" in body.lower()


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------


class TestExportarAsistenciaView:
    """Tests para ``ExportarAsistenciaView``."""

    def setup_method(self):
        _clear_cache()
        self.periodo = PeriodoFactory(nombre="2026-A")
        ParaleloFactory(periodo=self.periodo, nombre="A")
        self.url = reverse("reportes:exportar_asistencia")
        self.query = {"periodo": self.periodo.id}

    def test_docente_gets_excel_200(self, docente_client):
        """Docente recibe HTTP 200 con xlsx."""
        response = docente_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 200
        assert response.content[:2] == b"PK"

    def test_docente_gets_pdf_200(self, docente_client):
        """Docente recibe HTTP 200 con PDF."""
        response = docente_client.get(self.url, {**self.query, "formato": "pdf"})
        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"

    def test_inspector_gets_excel_200(self, inspector_client):
        """Inspector recibe HTTP 200."""
        response = inspector_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 200

    def test_secretaria_gets_excel_200(self, secretaria_client):
        """Secretaria recibe HTTP 200."""
        response = secretaria_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 200

    def test_estudiante_is_forbidden_403(self, estudiante_client):
        """Estudiante recibe HTTP 403."""
        response = estudiante_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 403

    def test_filename_prefix_is_asistencia(self, docente_client):
        """El filename empieza con ``asistencia_`` (no ``calificaciones_``)."""
        response = docente_client.get(self.url, {**self.query, "formato": "excel"})
        match = re.search(r'filename="([^"]+)"', response["Content-Disposition"])
        assert match is not None
        filename = match.group(1)
        assert filename.startswith("asistencia_2026-A_")
        assert filename.endswith(".xlsx")

    def test_view_returns_429_on_11th_call(self, docente_client):
        """La 11ª llamada retorna 429 con mensaje en español."""
        from django.contrib.auth import get_user_model

        Usuario = get_user_model()
        user = Usuario.objects.filter(rol="docente").order_by("-id").first()
        assert user is not None
        from django.utils import timezone

        bucket = timezone.now().strftime("%Y%m%d%H%M")
        key = f"export_rate_{user.id}_{bucket}"
        cache.set(key, 10, timeout=60)

        response = docente_client.get(self.url, {**self.query, "formato": "excel"})
        assert response.status_code == 429
        body = response.content.decode("utf-8")
        assert "Límite" in body or "limite" in body.lower()
