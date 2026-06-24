"""
Tests para la distribución de Reportes en el sidebar + 4 inline buttons
+ accessibility audit (HU27b WU5).

Cubre:
    - T5.1 / T5.2  Sidebar muestra "Reportes" para docente/inspector/secretaria
                   y NO para estudiante/anónimo (R20). El link apunta a
                   ``{% url "reportes:hub" %}`` = ``/reportes/``.
    - T5.3 / T5.4  Inline export buttons aparecen en 4 páginas documentadas
                   y SOLO para los roles correctos (R21 dashboard_rendimiento,
                   R22 seleccionar_paralelo, R23 auditoria_calificaciones,
                   R24 usuarios/dashboard).
    - T5.5 / T5.6  axe-core scan (opcional, skip si no está instalado).
    - T5.7        Smoke test: cada página sigue renderizando sin
                   ``TemplateSyntaxError`` ni ``TemplateDoesNotExist``.

Spec: R20, R21, R22, R23, R24, R26.
Design: §3 (NEW + EDITED), §4.2 (inline button callsites).
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

from tests.factories import ParaleloFactory, PeriodoFactory


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(settings.BASE_DIR)
SIDEBAR = REPO_ROOT / "templates" / "partials" / "sidebar.html"
SIDEBAR_REPORTES = REPO_ROOT / "templates" / "partials" / "_sidebar_reportes.html"
INLINE_EXPORT = REPO_ROOT / "templates" / "reportes" / "_partials" / "_inline_export.html"
HUB_URL = "/reportes/"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_dashboard(client):
    """Helper: renderiza ``/usuarios/dashboard/`` (incluye sidebar via base.html)."""
    return client.get("/usuarios/dashboard/")


# ---------------------------------------------------------------------------
# T5.1 / T5.2 — Sidebar
# ---------------------------------------------------------------------------


class TestSidebarReportesEntry:
    """El sidebar muestra "Reportes" para los 3 roles operacionales (R20)."""

    def test_sidebar_includes_reportes_partial(self):
        """``sidebar.html`` incluye ``_sidebar_reportes.html`` (D5)."""
        assert SIDEBAR.exists(), f"Sidebar missing: {SIDEBAR}"
        html = _read(SIDEBAR)
        assert (
            '{% include "partials/_sidebar_reportes.html"' in html
        ), "sidebar.html must include _sidebar_reportes.html partial"

    def test_sidebar_reportes_partial_exists(self):
        """El partial ``_sidebar_reportes.html`` existe."""
        assert SIDEBAR_REPORTES.exists(), f"Partial missing: {SIDEBAR_REPORTES}"

    def test_sidebar_reportes_partial_has_hub_link(self):
        """El partial tiene un ``<a>`` que apunta a ``{% url 'reportes:hub' %}``."""
        assert SIDEBAR_REPORTES.exists()
        html = _read(SIDEBAR_REPORTES)
        assert (
            "{% url 'reportes:hub'" in html
        ), "_sidebar_reportes.html must link to {% url 'reportes:hub' %}"

    def test_sidebar_includes_partial_in_3_role_blocks(self):
        """El include aparece en 3 role-gated blocks (docente, inspector, secretaria).

        El sidebar NO usa un solo bloque "3 roles" — tiene un
        ``{% if user.rol == 'X' %}`` por rol. El partial debe estar
        dentro de los 3 bloques que dan acceso a /reportes/.
        """
        html = _read(SIDEBAR)
        # El conteo mínimo es 3 (uno por cada rol operacional). Puede ser
        # más si hay un bloque combinado extra.
        count = html.count('{% include "partials/_sidebar_reportes.html"')
        assert count >= 3, (
            f"Expected at least 3 includes of _sidebar_reportes.html "
            f"(docente, inspector, secretaria), found {count}"
        )


class TestSidebarReportesRoleGate:
    """El link "Reportes" se muestra para los 3 roles y NO para estudiante."""

    @pytest.mark.parametrize(
        "client_fixture_name,expected_present",
        [
            ("docente_client", True),
            ("inspector_client", True),
            ("secretaria_client", True),
        ],
    )
    def test_sidebar_reportes_visible_for_operational_roles(
        self, request, client_fixture_name, expected_present
    ):
        """Docente, inspector, secretaria: ven el link "Reportes" en el sidebar."""
        client = request.getfixturevalue(client_fixture_name)
        response = _render_dashboard(client)
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El link debe estar presente con el href al hub
        assert "Reportes" in html, f"Expected 'Reportes' link in sidebar for {client_fixture_name}"
        # Y debe apuntar al hub
        assert HUB_URL in html, f"Expected hub URL {HUB_URL} in sidebar for {client_fixture_name}"

    def test_sidebar_reportes_oculto_estudiante(self, estudiante_client):
        """Estudiante: NO ve el link "Reportes" en el sidebar."""
        response = _render_dashboard(estudiante_client)
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El texto "Reportes" en el sidebar significa el link. Pero el
        # estudiante podría ver "Reportes" como parte de otra copy
        # (palabra común en español). Verificamos que el href al hub
        # no aparezca como link en el sidebar.
        # Estrategia: el href aparece solo si el link está renderizado.
        # En el sidebar, los links de navegación están dentro de <aside>...</aside>.
        aside_match = re.search(r"<aside[^>]*>(.*?)</aside>", html, re.DOTALL)
        assert aside_match is not None, "Sidebar <aside> not found in response"
        aside_html = aside_match.group(1)
        assert (
            HUB_URL not in aside_html
        ), "Sidebar for estudiante must NOT contain the Reportes hub link"


# ---------------------------------------------------------------------------
# T5.3 / T5.4 — Inline export buttons en las 4 páginas
# ---------------------------------------------------------------------------


class TestInlineButtonsDashboardRendimiento:
    """Inline buttons en ``dashboard_rendimiento`` para inspector+secretaria (R21)."""

    @pytest.mark.parametrize(
        "client_fixture_name",
        ["inspector_client", "secretaria_client"],
    )
    def test_dashboard_rendimiento_tiene_inline_buttons(
        self, request, client_fixture_name, hub_periodo_con_docente
    ):
        """Inspector/secretaria ven el inline button group en dashboard_rendimiento."""
        client = request.getfixturevalue(client_fixture_name)
        response = client.get(
            "/academico/dashboard-rendimiento/?tipo_licencia="
            f"{hub_periodo_con_docente.tipo_licencia_id}&periodo="
            f"{hub_periodo_con_docente.id}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        html = response.content.decode("utf-8")
        # El partial inyecta los hrefs del endpoint de export
        assert (
            "/reportes/calificaciones/exportar/?formato=excel" in html
        ), "Expected calificaciones Excel href in dashboard_rendimiento"
        assert (
            "/reportes/calificaciones/exportar/?formato=pdf" in html
        ), "Expected calificaciones PDF href in dashboard_rendimiento"

    def test_dashboard_rendimiento_docente_403(self, docente_client):
        """Docente: el view da 403 (no en roles_permitidos)."""
        response = docente_client.get("/academico/dashboard-rendimiento/")
        assert response.status_code == 403

    def test_dashboard_rendimiento_estudiante_403(self, estudiante_client):
        """Estudiante: el view da 403."""
        response = estudiante_client.get("/academico/dashboard-rendimiento/")
        assert response.status_code == 403

    def test_dashboard_rendimiento_buttons_carry_aria_labels(self, inspector_client):
        """Los inline buttons tienen ``aria-label`` (R26 a11y)."""
        response = inspector_client.get("/academico/dashboard-rendimiento/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El partial incluye aria-label en cada <a>
        assert "aria-label" in html, "Inline export buttons must have aria-label for a11y (R26)"


class TestInlineButtonsSeleccionarParalelo:
    """Inline buttons per paralelo en ``seleccionar_paralelo`` para docente (R22)."""

    def test_docente_ve_inline_buttons_por_paralelo(self, docente_client, hub_periodo_con_docente):
        """Docente con paralelos: cada card tiene inline buttons."""
        # El fixture hub_periodo_con_docente crea un Paralelo para el docente
        response = docente_client.get("/calificaciones/paralelos/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El partial inyecta los hrefs del endpoint de export + show_asistencia
        assert (
            "/reportes/calificaciones/exportar/?formato=excel" in html
        ), "Expected calificaciones Excel href per paralelo card"
        assert (
            "/reportes/calificaciones/exportar/?formato=pdf" in html
        ), "Expected calificaciones PDF href per paralelo card"
        # show_asistencia=True agrega los 2 botones de asistencia
        assert (
            "/reportes/asistencia/exportar/?formato=excel" in html
        ), "Expected asistencia Excel href per paralelo card"
        assert (
            "/reportes/asistencia/exportar/?formato=pdf" in html
        ), "Expected asistencia PDF href per paralelo card"

    def test_inspector_seleccionar_paralelo_403(self, inspector_client):
        """Inspector: 403 (el view es docente-only)."""
        response = inspector_client.get("/calificaciones/paralelos/")
        assert response.status_code == 403

    def test_seleccionar_paralelo_partial_includes_parallelo_id(
        self, docente_client, hub_periodo_con_docente
    ):
        """Los hrefs incluyen el ``paralelo`` actual como query param (R22)."""
        # Encontrar el paralelo del docente
        from apps.academico.infrastructure.models import Paralelo as ParaleloModel

        paralelo = ParaleloModel.objects.filter(docente__username="docente_test").first()
        if paralelo is None:
            pytest.skip("No paralelo for docente — fixture not in effect")
        response = docente_client.get("/calificaciones/paralelos/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert (
            f"paralelo={paralelo.id}" in html
        ), f"Expected paralelo={paralelo.id} in hrefs; not found"


class TestInlineButtonsAuditoriaCalificaciones:
    """Inline buttons en ``auditoria_calificaciones`` para inspector+secretaria (R23)."""

    @pytest.mark.parametrize(
        "client_fixture_name",
        ["inspector_client", "secretaria_client"],
    )
    def test_auditoria_tiene_inline_buttons(self, request, client_fixture_name):
        """Inspector/secretaria ven el inline button group en auditoría."""
        client = request.getfixturevalue(client_fixture_name)
        response = client.get("/calificaciones/auditoria/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert (
            "/reportes/calificaciones/exportar/?formato=excel" in html
        ), "Expected calificaciones Excel href in auditoria header"
        assert (
            "/reportes/calificaciones/exportar/?formato=pdf" in html
        ), "Expected calificaciones PDF href in auditoria header"

    @pytest.mark.parametrize(
        "client_fixture_name",
        ["docente_client", "estudiante_client"],
    )
    def test_auditoria_docente_estudiante_403(self, request, client_fixture_name):
        """Docente y estudiante: 403 (no en roles_permitidos)."""
        client = request.getfixturevalue(client_fixture_name)
        response = client.get("/calificaciones/auditoria/")
        assert response.status_code == 403


class TestQuickActionCardUsuariosDashboard:
    """Quick-action card en ``usuarios/dashboard`` para 3 roles (R24)."""

    @pytest.mark.parametrize(
        "client_fixture_name",
        ["docente_client", "inspector_client", "secretaria_client"],
    )
    def test_dashboard_tiene_quick_action_reportes(self, request, client_fixture_name):
        """Los 3 roles ven una quick-action card "Reportes" en el dashboard."""
        client = request.getfixturevalue(client_fixture_name)
        response = _render_dashboard(client)
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El quick-action card linkea a /reportes/
        assert HUB_URL in html, f"Expected {HUB_URL} in dashboard for {client_fixture_name}"
        # Y tiene un texto que identifica la card
        assert (
            "Reportes" in html
        ), f"Expected 'Reportes' text in dashboard for {client_fixture_name}"

    def test_dashboard_estudiante_NO_tiene_quick_action_reportes(self, estudiante_client):
        """Estudiante: NO ve la quick-action card (3 roles only)."""
        response = _render_dashboard(estudiante_client)
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # La quick-action card linkea a /reportes/. Para estudiante,
        # el sidebar NO debe tener /reportes/ (test de sidebar ya cubre eso)
        # y la quick-action card NO debe estar renderizada.
        # ESTRATEGIA: contar ocurrencias de /reportes/ en la página entera.
        # Para estudiante, debe haber 0 (no sidebar, no quick-action).
        # Para otros roles, hay >= 1 (sidebar + quick-action).
        # (El hub URL aparece en el sidebar Y en la quick-action card.)
        assert HUB_URL not in html, (
            "Estudiante dashboard must NOT contain any /reportes/ link "
            "(no sidebar entry, no quick-action card)"
        )


# ---------------------------------------------------------------------------
# T5.4 — Filters passed from page state into export URL
# ---------------------------------------------------------------------------


class TestInlineButtonsContextFilters:
    """Los hrefs del inline button heredan el ``periodo`` del page state (R21-R23)."""

    def test_dashboard_rendimiento_periodo_en_href(
        self, inspector_client, hub_periodo_con_docente
    ):
        """El href del inline button incluye el ``periodo`` actual del page."""
        response = inspector_client.get(
            "/academico/dashboard-rendimiento/?tipo_licencia="
            f"{hub_periodo_con_docente.tipo_licencia_id}&periodo="
            f"{hub_periodo_con_docente.id}"
        )
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El href de export debe incluir el periodo
        assert (
            f"periodo={hub_periodo_con_docente.id}" in html
        ), f"Expected periodo={hub_periodo_con_docente.id} in href"

    def test_auditoria_calificaciones_no_filter_in_href(self, inspector_client):
        """El href del inline button en auditoría no requiere periodo (R23
        permite periodo o filtros de fecha — el partial usa periodo si está).

        Verificamos que el href de la export URL tenga formato correcto,
        sin asumir que periodo está presente.
        """
        response = inspector_client.get("/calificaciones/auditoria/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El href de export debe estar presente y bien formado
        assert "/reportes/calificaciones/exportar/?formato=excel" in html


# ---------------------------------------------------------------------------
# T5.4 — Progressive enhancement: cada <a> es un link nativo
# ---------------------------------------------------------------------------


class TestInlineButtonsProgressiveEnhancement:
    """Cada inline button es un ``<a href>`` nativo (R19)."""

    def test_inline_export_partial_uses_native_anchors(self):
        """El partial ``_inline_export.html`` usa ``<a href>`` nativos (no <button>)."""
        assert INLINE_EXPORT.exists(), f"Inline export partial missing: {INLINE_EXPORT}"
        html = _read(INLINE_EXPORT)
        # Cada botón es un <a> con href al endpoint de export
        assert "<a " in html, "Inline buttons must use <a> for progressive enhancement"
        assert "href=" in html, "Inline buttons must have href="
        # El href apunta al endpoint de export real
        assert (
            "reportes:exportar_calificaciones" in html
        ), "Inline button href must point to reportes:exportar_calificaciones"

    def test_inline_export_partial_aria_labels(self):
        """Cada inline button tiene ``aria-label`` (R26 a11y)."""
        assert INLINE_EXPORT.exists()
        html = _read(INLINE_EXPORT)
        # Conteo de aria-label >= número de buttons
        aria_count = html.count("aria-label=")
        # 2 buttons por defecto (Excel + PDF) + 2 si show_asistencia = 4 max
        assert (
            aria_count >= 2
        ), f"Expected at least 2 aria-label attributes (Excel + PDF), got {aria_count}"

    def test_inline_export_partial_renders_with_periodo(self):
        """El partial renderiza con un contexto mínimo (periodo, paralelo)."""
        assert INLINE_EXPORT.exists()
        ctx = {
            "periodo": 1,
            "paralelo": 2,
        }
        try:
            html = render_to_string("reportes/_partials/_inline_export.html", context=ctx)
        except Exception as e:
            pytest.fail(f"_inline_export.html failed to render: {e}")
        # El href debe incluir periodo=1 y paralelo=2
        assert "periodo=1" in html, "Expected periodo=1 in href"
        assert "paralelo=2" in html, "Expected paralelo=2 in href"
        # Y los 2 buttons mínimos
        assert html.count("/reportes/calificaciones/exportar/") >= 2

    def test_inline_export_partial_show_asistencia_flag(self):
        """Con ``show_asistencia=True`` el partial agrega 2 buttons de asistencia."""
        assert INLINE_EXPORT.exists()
        ctx = {"periodo": 1, "paralelo": 2, "show_asistencia": True}
        html = render_to_string("reportes/_partials/_inline_export.html", context=ctx)
        # 2 buttons de calificaciones + 2 de asistencia = 4
        assert html.count("/reportes/calificaciones/exportar/") >= 2
        assert html.count("/reportes/asistencia/exportar/") >= 2

    def test_inline_export_partial_renders_with_only_periodo(self):
        """Sin ``paralelo``, los hrefs no incluyen ese param (all-paralelos fallback)."""
        assert INLINE_EXPORT.exists()
        ctx = {"periodo": 1}
        try:
            html = render_to_string("reportes/_partials/_inline_export.html", context=ctx)
        except Exception as e:
            pytest.fail(f"_inline_export.html failed without paralelo: {e}")
        # periodo=1 está; paralelo no
        assert "periodo=1" in html
        # Los 2 buttons de calificaciones están
        assert "/reportes/calificaciones/exportar/?formato=excel" in html
        assert "/reportes/calificaciones/exportar/?formato=pdf" in html


# ---------------------------------------------------------------------------
# T5.5 — axe-core accessibility scan (opcional, skip si no está instalado)
# ---------------------------------------------------------------------------


class TestAxeCoreAccessibility:
    """a11y: axe-core scan de las páginas con nuevos componentes (R26, D10)."""

    @pytest.mark.skipif(
        True,  # Skip por ahora — no hay axe-core-python instalado
        reason="axe-core-python not installed; manual a11y checklist instead",
    )
    def test_hub_axe_core_zero_violations(self, docente_client):
        """El hub tiene 0 violations de WCAG 2/2.1 A/AA."""
        # Si axe-core-python estuviera disponible:
        # from axe_core_python.sync_playwright import Axe
        # axe = Axe()
        # response = docente_client.get("/reportes/")
        # results = axe.run(html=response.content)
        # assert results.violations == []
        pass

    def test_dashboard_rendimiento_inline_buttons_aria_buttons(
        self, inspector_client, hub_periodo_con_docente
    ):
        """Verificación mínima de a11y: aria-label presente y ``role`` correcto."""
        response = inspector_client.get(
            "/academico/dashboard-rendimiento/?tipo_licencia="
            f"{hub_periodo_con_docente.tipo_licencia_id}"
        )
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El partial envuelve los buttons en role="group" con aria-label
        assert (
            'role="group"' in html
        ), "Inline export button group must have role='group' (R26 a11y)"
        assert 'aria-label="Exportar reportes"' in html or (
            'aria-label="exportar"' in html.lower()
        ), "Inline export button group must have aria-label (R26 a11y)"


# ---------------------------------------------------------------------------
# T5.7 — Smoke: las 4 páginas siguen renderizando sin error
# ---------------------------------------------------------------------------


class TestSmokeRender:
    """Smoke: las 4 páginas con nuevos componentes renderizan sin error."""

    def test_dashboard_rendimiento_smoke(self, inspector_client):
        """dashboard_rendimiento: 200 OK y contiene el contenido esperado."""
        response = inspector_client.get("/academico/dashboard-rendimiento/")
        assert response.status_code == 200
        # Sin TemplateSyntaxError ni TemplateDoesNotExist — el assert 200 lo cubre

    def test_seleccionar_paralelo_smoke(self, docente_client, hub_periodo_con_docente):
        """seleccionar_paralelo: 200 OK."""
        response = docente_client.get("/calificaciones/paralelos/")
        assert response.status_code == 200

    def test_auditoria_smoke(self, inspector_client):
        """auditoria_calificaciones: 200 OK."""
        response = inspector_client.get("/calificaciones/auditoria/")
        assert response.status_code == 200

    def test_usuarios_dashboard_smoke(self, docente_client):
        """usuarios/dashboard: 200 OK."""
        response = docente_client.get("/usuarios/dashboard/")
        assert response.status_code == 200

    def test_hub_smoke(self, docente_client):
        """El hub sigue renderizando OK después de WU5."""
        response = docente_client.get("/reportes/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # El hub sigue mostrando los 2 cards
        assert "Calificaciones" in html
        assert "Asistencia" in html


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hub_periodo(db):
    """Periodo válido con todas las FK requeridas (tipo_licencia)."""
    return PeriodoFactory(nombre="2026-A", activo=True)


@pytest.fixture
def hub_periodo_con_docente(db, hub_periodo, docente):
    """Periodo con un paralelo asignado al docente (mirror de test_hub)."""
    ParaleloFactory(periodo=hub_periodo, docente=docente, nombre="A")
    return hub_periodo
