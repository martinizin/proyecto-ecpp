"""Structural guards for the persistent navigation chrome (sidebar + topbar).

Issue 4 fixed two ways the "Cerrar Sesión" control could disappear on a phone:

1. The topbar user dropdown was gated behind ``hidden sm:block``, so below
   640px the only visible control was the notification bell.
2. The sidebar panel was sized with ``h-screen`` (100vh). On mobile browsers
   100vh measures the *large* viewport — the one with the URL bar hidden — so
   the panel footer that holds the logout link rendered past the bottom of the
   visible area, and ``overflow-hidden`` made it unreachable.

These tests are structural only (no JS runtime / pixel checks); see
docs/responsive-convention.md for the manual-QA matrix that complements them.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from tests.factories import SecretariaFactory


pytestmark = pytest.mark.django_db


REPO_ROOT = Path(settings.BASE_DIR)
BASE_HTML = REPO_ROOT / "templates" / "base.html"
SIDEBAR = REPO_ROOT / "templates" / "partials" / "sidebar.html"
TOPBAR = REPO_ROOT / "templates" / "partials" / "topbar.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture
def secretaria_dashboard(client):
    """Render the dashboard as secretaría — the role with every sidebar section."""
    user = SecretariaFactory()
    user.save()
    client.force_login(user)
    response = client.get(reverse("usuarios:dashboard"))
    assert response.status_code == 200
    return response.content.decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Logout reachability
# ══════════════════════════════════════════════════════════════════════════════


class TestLogoutSiempreAlcanzable:
    """El control de cerrar sesión existe en topbar y sidebar en todo breakpoint."""

    def test_topbar_user_menu_not_hidden_on_mobile(self):
        """El dropdown de usuario no está oculto por debajo de ``sm``."""
        html = _read(TOPBAR)
        assert (
            'class="hidden sm:block" x-data="{ userOpen: false }"' not in html
        ), "Topbar user menu must not be hidden below the sm breakpoint"

    def test_topbar_renders_logout_link(self, secretaria_dashboard):
        """El topbar renderiza el link de logout."""
        logout_url = reverse("usuarios:logout")
        assert f'href="{logout_url}"' in secretaria_dashboard
        assert "Cerrar Sesión" in secretaria_dashboard

    def test_topbar_user_menu_is_announced_as_a_menu(self):
        """El trigger del dropdown tiene nombre accesible y estado expandido."""
        html = _read(TOPBAR)
        assert 'aria-label="Menú de usuario"' in html
        assert 'aria-haspopup="true"' in html
        assert ":aria-expanded=" in html

    def test_sidebar_renders_logout_link(self, secretaria_dashboard):
        """El sidebar renderiza su propio link de logout en el footer."""
        html = _read(SIDEBAR)
        assert "{% url 'usuarios:logout' %}" in html
        assert "Cerrar Sesión" in html


class TestSidebarAlturaViewportVisible:
    """El panel del sidebar se mide contra el viewport visible, no contra 100vh."""

    def test_sidebar_no_usa_h_screen(self):
        """``h-screen`` empuja el footer (y el logout) fuera de pantalla en mobile."""
        html = _read(SIDEBAR)
        assert (
            "h-screen" not in html
        ), "Sidebar panel must not use h-screen — its footer falls below the mobile fold"

    def test_sidebar_usa_clase_sidebar_panel(self):
        """El ``<aside>`` usa la clase ``sidebar-panel``."""
        html = _read(SIDEBAR)
        assert "sidebar-panel" in html

    def test_base_define_sidebar_panel_con_dvh_y_fallback(self):
        """``.sidebar-panel`` declara 100vh (fallback) y luego 100dvh."""
        css = _read(BASE_HTML)
        assert (
            ".sidebar-panel { height: 100vh; height: 100dvh; }" in css
        ), "base.html must define .sidebar-panel with a 100vh fallback before 100dvh"


# ══════════════════════════════════════════════════════════════════════════════
# Orden de los items del sidebar
# ══════════════════════════════════════════════════════════════════════════════


class TestSidebarOrdenReportes:
    """Issue 4: el hub de Reportes se ubica debajo de Reportes ANT."""

    _INCLUDE = '{% include "partials/_sidebar_reportes.html" %}'

    def test_reportes_hub_va_debajo_de_reportes_ant(self):
        """En el bloque de secretaría, el include del hub sigue al link de ANT."""
        html = _read(SIDEBAR)
        ant = html.index("{% url 'reportes:ant_listado' %}")
        includes = [i for i in range(len(html)) if html.startswith(self._INCLUDE, i)]
        assert includes, "sidebar.html must include _sidebar_reportes.html"
        assert any(
            i > ant for i in includes
        ), "The Reportes hub link must be rendered after the Reportes ANT link"

    def test_reportes_hub_no_queda_dentro_de_calificaciones(self):
        """El include ya no cuelga de la sección Calificaciones de secretaría."""
        html = _read(SIDEBAR)
        validar = html.index("{% url 'calificaciones:pendientes_validacion' %}")
        ant = html.index("{% url 'reportes:ant_listado' %}")
        assert (
            self._INCLUDE not in html[validar:ant]
        ), "Reportes hub must not sit between Validar Calificaciones and Reportes ANT"

    def test_secretaria_ve_hub_y_ant(self, secretaria_dashboard):
        """Secretaría ve ambos links renderizados."""
        assert reverse("reportes:hub") in secretaria_dashboard
        assert reverse("reportes:ant_listado") in secretaria_dashboard
