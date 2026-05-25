"""HU21 T8 - Link swap a nuevo dashboard del inspector.

Regression suite que garantiza:
1. La URL legacy `solicitudes:pendientes_justificacion` sigue VIVA (HU18-style
   deprecation): los deep-links existentes no se rompen.
2. Ningun template de UI referencia ya la URL vieja por nombre.
3. Los 3 templates afectados linkean al nuevo dashboard
   `solicitudes:inspector_justificaciones_dashboard` (HU21 T4).
4. El active-state matcher del sidebar fue portado al nuevo url_name.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse


TEMPLATES = [
    Path("templates/partials/sidebar.html"),
    Path("templates/usuarios/dashboard.html"),
    Path("templates/solicitudes/resolver_solicitud.html"),
]


def test_old_pendientes_justificacion_url_still_resolves():
    """HU18-style deprecation: la URL vieja debe seguir resolviendo."""
    url = reverse("solicitudes:pendientes_justificacion")
    assert url, "La URL legacy debe seguir registrada (deep-links preservados)"


def test_new_inspector_dashboard_url_resolves():
    """Sanity check: la URL nueva del dashboard del inspector existe."""
    url = reverse("solicitudes:inspector_justificaciones_dashboard")
    assert url


@pytest.mark.parametrize("template_path", TEMPLATES)
def test_template_no_referencia_old_url(template_path):
    """Ninguno de los 3 templates puede seguir referenciando la URL vieja."""
    content = template_path.read_text(encoding="utf-8")
    pattern = r"\{\%\s*url\s+['\"]solicitudes:pendientes_justificacion['\"]"
    assert not re.search(pattern, content), (
        f"{template_path} still references the old URL " f"`solicitudes:pendientes_justificacion`"
    )


@pytest.mark.parametrize("template_path", TEMPLATES)
def test_template_referencia_new_url(template_path):
    """Los 3 templates deben linkear al nuevo dashboard del inspector."""
    content = template_path.read_text(encoding="utf-8")
    pattern = r"\{\%\s*url\s+['\"]solicitudes:inspector_justificaciones_dashboard['\"]"
    assert re.search(pattern, content), (
        f"{template_path} doesn't reference the new inspector dashboard URL "
        f"`solicitudes:inspector_justificaciones_dashboard`"
    )


def test_sidebar_active_state_matcher_uses_new_url_name():
    """El active-state matcher del sidebar debe usar el url_name nuevo,
    no el legacy `pendientes_justificacion`."""
    content = Path("templates/partials/sidebar.html").read_text(encoding="utf-8")
    # Old url_name should NOT appear in resolver_match comparisons.
    assert "resolver_match.url_name == 'pendientes_justificacion'" not in content
    assert 'resolver_match.url_name == "pendientes_justificacion"' not in content
    # New url_name MUST appear in at least one resolver_match comparison.
    has_new_matcher = (
        "resolver_match.url_name == 'inspector_justificaciones_dashboard'" in content
        or 'resolver_match.url_name == "inspector_justificaciones_dashboard"' in content
    )
    assert has_new_matcher, (
        "Sidebar active-state matcher must reference " "`inspector_justificaciones_dashboard`"
    )
