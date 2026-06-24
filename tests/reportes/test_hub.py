"""
Tests para el hub de Reportes (HU27b WU4).

El hub es la página ``GET /reportes/`` que muestra 2 cards de export
(Calificaciones, Asistencia) con preview en vivo y botones de descarga
que funcionan con y sin Alpine (progressive enhancement).

Cubre:
    - T4.1  El hub retorna 200 para los 3 roles operacionales
            (docente, inspector, secretaria) y rechaza estudiante
            con 403 (R12).
    - T4.2  Anónimo → redirect a login (302).
            El contexto tiene ``periodo_actual``, ``periodos_disponibles``,
            ``paralelos_disponibles`` (role-aware, WU2).
            Query string ``?periodo=N`` pre-selecciona ese periodo.
    - T4.3  La view existe, está montada en ``/reportes/`` con name
            ``hub`` y renderiza ``templates/reportes/hub.html``.
    - T4.6  El template define ``function exportFlow()`` + tokens clave
            (3 ramas de toast, ``URL.createObjectURL`` / revoke).
    - T4.7  Los botones de export son progressive enhancement: cada
            uno es un ``<a href="...">`` con también un ``@click``
            que llama a ``download()``.

Spec: R12, R13, R15, R17, R18, R19, R24, R26.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from tests.factories import ParaleloFactory, PeriodoFactory


pytestmark = pytest.mark.django_db


@pytest.fixture
def hub_periodo(db):
    """Periodo válido con todas las FK requeridas (tipo_licencia).

    Reemplaza el ``active_periodo`` de ``tests/conftest.py`` que quedó
    desactualizado tras el cambio de schema en WU2.
    """
    return PeriodoFactory(nombre="2026-A", activo=True)


@pytest.fixture
def hub_periodo_con_docente(db, hub_periodo, docente):
    """Periodo con un paralelo asignado al ``docente``.

    El docente del conftest por defecto no tiene paralelos; sin un
    paralelo, ``ReportesDisponibilidadService.obtener_periodos_disponibles``
    retorna lista vacía y el hub no puede pre-seleccionar el periodo.
    Esta fixture crea el paralelo necesario para que los role-aware
    filters del WU2 devuelvan el periodo al docente.
    """
    ParaleloFactory(periodo=hub_periodo, docente=docente, nombre="A")
    return hub_periodo


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(settings.BASE_DIR)
HUB_HTML = REPO_ROOT / "templates" / "reportes" / "hub.html"
CARD_CAL = REPO_ROOT / "templates" / "reportes" / "_partials" / "card_calificaciones.html"
CARD_ASI = REPO_ROOT / "templates" / "reportes" / "_partials" / "card_asistencia.html"
PREVIEW_PANE = REPO_ROOT / "templates" / "reportes" / "_partials" / "preview_pane.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_hub(client):
    """Helper: renderiza el hub como ``client`` (debe estar autenticado
    con un rol de los 3 permitidos)."""
    return client.get("/reportes/")


# ---------------------------------------------------------------------------
# T4.1 — 3 roles retornan 200, estudiante 403
# ---------------------------------------------------------------------------


class TestHubRoleGate:
    """El hub permite los 3 roles operacionales y rechaza estudiante."""

    def test_hub_docente_200(self, docente_client):
        """Docente: GET /reportes/ → 200."""
        response = _render_hub(docente_client)
        assert response.status_code == 200, f"Expected 200 for docente, got {response.status_code}"

    def test_hub_inspector_200(self, inspector_client):
        """Inspector: GET /reportes/ → 200."""
        response = _render_hub(inspector_client)
        assert response.status_code == 200

    def test_hub_secretaria_200(self, secretaria_client):
        """Secretaria: GET /reportes/ → 200."""
        response = _render_hub(secretaria_client)
        assert response.status_code == 200

    def test_hub_estudiante_403(self, estudiante_client):
        """Estudiante: GET /reportes/ → 403 (R12, denegado por MultiRolRequeridoMixin)."""
        response = _render_hub(estudiante_client)
        assert response.status_code == 403


class TestHubAnonymousRedirect:
    """Sin autenticación, el hub redirige a login (R12)."""

    def test_hub_sin_login_redirige_login(self, client):
        """Anonymous: GET /reportes/ → 302 a /usuarios/login/."""
        response = _render_hub(client)
        # LoginRequiredMixin redirecta a LOGIN_URL. Aceptamos 302 con Location.
        assert (
            response.status_code == 302
        ), f"Expected 302 (redirect to login) for anonymous, got {response.status_code}"
        location = response.get("Location", "")
        assert (
            "login" in location.lower()
        ), f"Expected redirect to login, got Location={location!r}"


# ---------------------------------------------------------------------------
# T4.2 — Contexto: periodos + paralelos role-aware
# ---------------------------------------------------------------------------


class TestHubContext:
    """El contexto provee los datos role-aware del WU2."""

    def test_hub_context_has_periodos_disponibles(self, docente_client, hub_periodo_con_docente):
        """El contexto expone ``periodos_disponibles`` (lista de Periodo)."""
        hub_periodo = hub_periodo_con_docente
        response = _render_hub(docente_client)
        assert response.status_code == 200
        assert "periodos_disponibles" in response.context
        assert "periodo_actual" in response.context
        # La lista de periodos disponibles incluye el periodo activo
        ids = [p.id for p in response.context["periodos_disponibles"]]
        assert hub_periodo.id in ids

    def test_hub_context_has_paralelos_disponibles(self, docente_client, hub_periodo_con_docente):
        """El contexto expone ``paralelos_disponibles`` cuando hay periodo_actual."""
        response = _render_hub(docente_client)
        assert "paralelos_disponibles" in response.context

    def test_hub_pre_select_periodo_desde_query_string(
        self, docente_client, hub_periodo_con_docente
    ):
        """GET /reportes/?periodo=N pre-selecciona el periodo N (si es válido)."""
        hub_periodo = hub_periodo_con_docente
        response = docente_client.get("/reportes/", {"periodo": str(hub_periodo.id)})
        assert response.status_code == 200
        # El context debe tener periodo_actual con el id pedido
        periodo_actual = response.context.get("periodo_actual")
        assert (
            periodo_actual is not None
        ), "Expected periodo_actual in context when ?periodo=N is provided"
        assert periodo_actual.id == hub_periodo.id

    def test_hub_invalid_periodo_query_falls_back_to_first(
        self, docente_client, hub_periodo_con_docente
    ):
        """Si el ?periodo=N no es válido, cae al primer periodo disponible."""
        hub_periodo = hub_periodo_con_docente
        # 99999 no existe en la DB
        response = docente_client.get("/reportes/", {"periodo": "99999"})
        assert response.status_code == 200
        periodo_actual = response.context.get("periodo_actual")
        # Debe caer al primer periodo (hub_periodo)
        assert periodo_actual is not None
        assert periodo_actual.id == hub_periodo.id


# ---------------------------------------------------------------------------
# T4.3 — Template usado + cards renderizadas
# ---------------------------------------------------------------------------


class TestHubTemplate:
    """El template es ``reportes/hub.html`` y renderiza ambos cards."""

    def test_hub_uses_correct_template(self, docente_client):
        """``assertTemplateUsed`` confirma que la view usa ``reportes/hub.html``."""
        response = _render_hub(docente_client)
        assertTemplateUsed(response, "reportes/hub.html")

    def test_hub_renderiza_card_calificaciones(self, docente_client):
        """El HTML contiene el título de la card Calificaciones."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        assert "Calificaciones" in html, "Card title 'Calificaciones' missing"

    def test_hub_renderiza_card_asistencia(self, docente_client):
        """El HTML contiene el título de la card Asistencia."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        assert "Asistencia" in html, "Card title 'Asistencia' missing"


# ---------------------------------------------------------------------------
# T4.6 — exportFlow() Alpine component contract
# ---------------------------------------------------------------------------


class TestExportFlowComponent:
    """El template define ``function exportFlow()`` + tokens del design §4.6."""

    def test_hub_renderiza_export_flow_alpine(self, docente_client):
        """El HTML renderizado contiene ``function exportFlow()``."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        assert (
            "function exportFlow()" in html
        ), "function exportFlow() must be in rendered hub HTML"

    def test_hub_template_uses_x_data_export_flow(self, docente_client):
        """El template usa ``x-data=\"exportFlow()\"`` en el contenedor."""
        html = _read(HUB_HTML)
        assert re.search(
            r'x-data="exportFlow\(\)"', html
        ), 'Hub template must declare x-data="exportFlow()" somewhere'

    @pytest.mark.parametrize(
        "token",
        [
            "function exportFlow()",
            "busy:",
            "URL.createObjectURL",
            "URL.revokeObjectURL",
            "toast:show",
            "Content-Disposition",
            "window.dispatchEvent",
        ],
    )
    def test_export_flow_partial_source_contains_token(self, token):
        """Cada token del design §4.6 (D8 + branch handling) está en el source."""
        html = _read(HUB_HTML)
        assert token in html, f"Missing required token in hub.html: {token!r}"

    def test_export_flow_handles_429_branch(self):
        """El source tiene una rama explícita para HTTP 429 (R17)."""
        html = _read(HUB_HTML)
        # Either via `=== 429` or `=== '429'` or `res.status === 429`
        assert re.search(
            r"status\s*[=!]==?\s*['\"]?429", html
        ), "exportFlow() must branch on status === 429 (R17)"

    def test_export_flow_handles_success_with_blob(self):
        """El source hace ``.blob()`` sobre la respuesta exitosa."""
        html = _read(HUB_HTML)
        assert ".blob()" in html, "exportFlow() must call .blob() on success (D8)"


# ---------------------------------------------------------------------------
# T4.6 — Preview pane (shared partial)
# ---------------------------------------------------------------------------


class TestPreviewPane:
    """El hub incluye el preview_pane partial."""

    def test_hub_renderiza_preview_pane(self, docente_client):
        """El HTML renderizado contiene un marker del preview_pane."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        # Aceptamos el marker comment del partial O el include string
        assert (
            "HUB-PREVIEW-PANE" in html
            or 'include "reportes/_partials/preview_pane.html"' in _read(HUB_HTML)
        ), "Preview pane must be included in hub"

    def test_preview_pane_partial_exists_and_renders(self):
        """El partial preview_pane.html existe y renderiza standalone."""
        from django.template.loader import render_to_string

        html = render_to_string("reportes/_partials/preview_pane.html", context={})
        # El partial debe mencionar el count y los sample rows
        assert (
            "estudiantes" in html or "count" in html or "sample" in html.lower()
        ), "Preview pane must mention count / estudiantes / sample"

    def test_preview_pane_partial_has_aria_live_region(self):
        """El preview_pane tiene ``aria-live`` para anunciar el count (R26 a11y)."""
        html = _read(PREVIEW_PANE)
        assert "aria-live" in html, "Preview pane must have aria-live region (R26)"

    def test_hub_template_includes_preview_pane_partial(self):
        """El preview_pane partial está incluido por el hub, directa o
        transitivamente (los cards incluyen el partial)."""
        html = _read(HUB_HTML)
        # Either hub.html includes it directly, or the cards (which hub
        # includes) include it. The cards are the documented place.
        if '{% include "reportes/_partials/preview_pane.html"' not in html:
            # Fallback: check the card partials include the preview pane
            for card_path in (CARD_CAL, CARD_ASI):
                card_html = _read(card_path)
                assert (
                    '{% include "reportes/_partials/preview_pane.html"' in card_html
                ), f"Neither hub.html nor {card_path.name} include preview_pane"


# ---------------------------------------------------------------------------
# T4.7 — Progressive enhancement: cada botón es un <a href> nativo
# ---------------------------------------------------------------------------


class TestProgressiveEnhancement:
    """R19: cada botón es un ``<a href="...">`` nativo + handler Alpine."""

    def test_calificaciones_card_has_excel_and_pdf_native_anchors(self, docente_client):
        """La card Calificaciones tiene <a href> para Excel y PDF."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        # El href debe apuntar al endpoint de export con formato
        assert "/reportes/calificaciones/exportar/?formato=excel" in html
        assert "/reportes/calificaciones/exportar/?formato=pdf" in html

    def test_asistencia_card_has_excel_and_pdf_native_anchors(self, docente_client):
        """La card Asistencia tiene <a href> para Excel y PDF."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        assert "/reportes/asistencia/exportar/?formato=excel" in html
        assert "/reportes/asistencia/exportar/?formato=pdf" in html

    def test_buttons_have_alpine_click_handler(self, docente_client):
        """Los anchors tienen ``@click.prevent=\"...\"`` para el fetch+blob path."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        # @click.prevent debe aparecer al menos una vez (es el patrón de PE)
        assert (
            "@click.prevent" in html
        ), "Export buttons must use @click.prevent to intercept native download"
        # Y debe llamar a download() o similar de exportFlow
        assert (
            "download(" in html or "descargar(" in html
        ), "Alpine click handler must call download()/descargar() in exportFlow"

    def test_buttons_carry_aria_busy_attribute(self, docente_client):
        """Los botones tienen ``:aria-busy`` o ``aria-busy`` para a11y (R24 a11y)."""
        response = _render_hub(docente_client)
        html = response.content.decode("utf-8")
        # Either static aria-busy or Alpine :aria-busy binding
        assert "aria-busy" in html, "Export buttons must have :aria-busy for a11y (R24)"

    def test_buttons_disabled_state_via_alpine_binding(self, docente_client):
        """Los botones tienen ``:disabled="busy"`` para evitar doble-click.

        El binding vive en los card partials (que el hub incluye), no en
        hub.html directamente. Verificamos ambos lugares.
        """
        for path in (CARD_CAL, CARD_ASI, HUB_HTML):
            html = _read(path)
            if re.search(r":disabled=", html):
                return  # at least one place has it
        raise AssertionError(
            "Export buttons must have :disabled binding tied to busy state "
            "(in hub.html or in the card partials)"
        )


# ---------------------------------------------------------------------------
# T4.3 — Card partials existen y son renderizables
# ---------------------------------------------------------------------------


class TestCardPartials:
    """Los partials de cada card existen y renderizan sin error."""

    def test_card_calificaciones_partial_exists(self):
        """``card_calificaciones.html`` existe."""
        assert CARD_CAL.exists(), f"Card partial missing: {CARD_CAL}"

    def test_card_asistencia_partial_exists(self):
        """``card_asistencia.html`` existe."""
        assert CARD_ASI.exists(), f"Card partial missing: {CARD_ASI}"

    def test_card_calificaciones_partial_renders_with_context(self, docente_client):
        """El partial de Calificaciones renderiza con context mínimo."""
        from django.template.loader import render_to_string

        # El partial puede depender de periodo_actual; proveemos un stub
        from types import SimpleNamespace

        ctx = {
            "periodo_actual": SimpleNamespace(id=1, nombre="2026-A"),
            "paralelos_disponibles": [],
        }
        try:
            html = render_to_string("reportes/_partials/card_calificaciones.html", context=ctx)
        except Exception as e:
            pytest.fail(f"card_calificaciones.html failed to render: {e}")
        assert "Calificaciones" in html
        # Los hrefs de los botones deben estar presentes
        assert "/reportes/calificaciones/exportar/?formato=excel" in html
        assert "/reportes/calificaciones/exportar/?formato=pdf" in html

    def test_card_asistencia_partial_renders_with_context(self, docente_client):
        """El partial de Asistencia renderiza con context mínimo."""
        from django.template.loader import render_to_string
        from types import SimpleNamespace

        ctx = {
            "periodo_actual": SimpleNamespace(id=1, nombre="2026-A"),
            "paralelos_disponibles": [],
        }
        try:
            html = render_to_string("reportes/_partials/card_asistencia.html", context=ctx)
        except Exception as e:
            pytest.fail(f"card_asistencia.html failed to render: {e}")
        assert "Asistencia" in html
        assert "/reportes/asistencia/exportar/?formato=excel" in html
        assert "/reportes/asistencia/exportar/?formato=pdf" in html

    def test_hub_includes_card_calificaciones(self):
        """hub.html incluye card_calificaciones.html."""
        html = _read(HUB_HTML)
        assert '{% include "reportes/_partials/card_calificaciones.html"' in html

    def test_hub_includes_card_asistencia(self):
        """hub.html incluye card_asistencia.html."""
        html = _read(HUB_HTML)
        assert '{% include "reportes/_partials/card_asistencia.html"' in html


# ---------------------------------------------------------------------------
# URL name registration
# ---------------------------------------------------------------------------


class TestHubUrl:
    """La URL del hub está registrada con name ``hub``."""

    def test_hub_url_name_resolves(self):
        """``reverse('reportes:hub')`` retorna '/reportes/'."""
        url = reverse("reportes:hub")
        assert url == "/reportes/", f"Expected /reportes/, got {url!r}"

    def test_hub_url_resolves_to_hub_view(self, docente_client):
        """Hacer GET al URL resuelto por name ``hub`` retorna 200."""
        url = reverse("reportes:hub")
        response = docente_client.get(url)
        assert response.status_code == 200
