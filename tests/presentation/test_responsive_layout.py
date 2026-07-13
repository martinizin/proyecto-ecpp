"""Structural regression guards for the responsive/mobile layout refactor (P1-P4).

Renders real pages via the Django test client and asserts on decoded HTML text.
These tests are structural only (no JS runtime / pixel checks) — see
docs/responsive-convention.md and
openspec/changes/responsive-refactor/spec.md for the manual-QA matrix that
complements these guards.
"""

import re

import pytest
from django.urls import reverse

from tests.factories import (
    DocenteFactory,
    EstudianteFactory,
    EvaluacionFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    SecretariaFactory,
    TipoLicenciaFactory,
)

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _saved(user):
    """Persist password hash so force_login session survives the request cycle."""
    user.save()
    return user


def _extract_tag(html, tag_name):
    """Returns the full opening tag text (e.g. '<main ...>') for the first
    match. Requires whitespace or '>' immediately after the tag name so a
    stray literal like '<aside>' inside a JS comment can't be mismatched for
    the real element. Treats quoted attribute values as atomic so a `>`
    inside an Alpine expression (e.g. an arrow function `=>`) doesn't
    truncate the match early."""
    pattern = rf"""<{tag_name}(?=[\s>])(?:[^>"']|"[^"]*"|'[^']*')*>"""
    match = re.search(pattern, html)
    assert match, f"<{tag_name}> not found in rendered HTML"
    return match.group(0)


def _bare_grid_cols(html):
    """Returns every `grid-cols-N` (N in 2-9) token that is NOT prefixed by a
    responsive breakpoint (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`)."""
    bare = []
    for m in re.finditer(r"(\S*)grid-cols-([2-9])\b", html):
        prefix = m.group(1)
        if not prefix.endswith(("sm:", "md:", "lg:", "xl:", "2xl:")):
            bare.append(m.group(0))
    return bare


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def docente_eval_page(client, db):
    """Authenticated docente GET on `gestionar_evaluaciones` — exercises the
    full authenticated shell (base.html, topbar.html, sidebar.html) plus the
    evaluaciones table."""
    docente = _saved(DocenteFactory())
    paralelo = ParaleloFactory(docente=docente)
    EvaluacionFactory(paralelo=paralelo)
    client.force_login(docente)
    url = reverse("calificaciones:gestionar_evaluaciones", kwargs={"paralelo_id": paralelo.pk})
    resp = client.get(url)
    assert resp.status_code == 200
    return resp.content.decode()


@pytest.fixture
def editar_evaluacion_page(client, db):
    docente = _saved(DocenteFactory())
    paralelo = ParaleloFactory(docente=docente)
    evaluacion = EvaluacionFactory(paralelo=paralelo)
    client.force_login(docente)
    url = reverse(
        "calificaciones:editar_evaluacion",
        kwargs={"paralelo_id": paralelo.pk, "evaluacion_id": evaluacion.pk},
    )
    resp = client.get(url)
    assert resp.status_code == 200
    return resp.content.decode()


@pytest.fixture
def usuario_create_page(client, db):
    secretaria = _saved(SecretariaFactory())
    client.force_login(secretaria)
    resp = client.get(reverse("secretaria:usuario_create"))
    assert resp.status_code == 200
    return resp.content.decode()


@pytest.fixture
def dashboard_rendimiento_page(client, db):
    tl = TipoLicenciaFactory(activo=True)
    periodo = PeriodoFactory(activo=True, tipo_licencia=tl)
    paralelo = ParaleloFactory(periodo=periodo, tipo_licencia=tl)
    estudiante = EstudianteFactory()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo)
    inspector = _saved(InspectorFactory())
    client.force_login(inspector)
    url = reverse("academico:dashboard_rendimiento")
    resp = client.get(url + f"?tipo_licencia={tl.id}&periodo={periodo.id}")
    assert resp.status_code == 200
    return resp.content.decode()


# ══════════════════════════════════════════════════════════════════════════════
# P1 — Main/Header offset gated to `lg` breakpoint
# ══════════════════════════════════════════════════════════════════════════════


class TestMainHeaderOffset:

    def test_main_has_no_unconditional_margin_left(self, docente_eval_page):
        main_tag = _extract_tag(docente_eval_page, "main")
        assert "margin-left" not in main_tag

    def test_main_has_lg_gated_offset_classes(self, docente_eval_page):
        main_tag = _extract_tag(docente_eval_page, "main")
        assert "lg:ml-16" in main_tag
        assert "lg:ml-64" in main_tag

    def test_header_has_no_unconditional_left_style(self, docente_eval_page):
        header_tag = _extract_tag(docente_eval_page, "header")
        assert ":style" not in header_tag
        assert "'left'" not in header_tag

    def test_header_has_lg_gated_offset_classes(self, docente_eval_page):
        header_tag = _extract_tag(docente_eval_page, "header")
        assert "lg:left-16" in header_tag
        assert "lg:left-64" in header_tag

    def test_tailwind_safelist_includes_offset_classes(self, docente_eval_page):
        assert "safelist" in docente_eval_page
        for cls in ("lg:ml-16", "lg:ml-64", "lg:left-16", "lg:left-64"):
            assert cls in docente_eval_page


# ══════════════════════════════════════════════════════════════════════════════
# P2 — Mobile drawer a11y (dialog semantics gated below `lg`) + focus mgmt
# ══════════════════════════════════════════════════════════════════════════════


class TestDrawerA11y:

    def test_aside_has_gated_role_binding(self, docente_eval_page):
        aside_tag = _extract_tag(docente_eval_page, "aside")
        assert ":role=" in aside_tag
        assert "dialog" in aside_tag

    def test_aside_has_gated_aria_modal_binding(self, docente_eval_page):
        aside_tag = _extract_tag(docente_eval_page, "aside")
        assert ":aria-modal=" in aside_tag
        assert "true" in aside_tag

    def test_aside_has_escape_and_tab_handlers(self, docente_eval_page):
        aside_tag = _extract_tag(docente_eval_page, "aside")
        assert "@keydown.escape.window" in aside_tag
        assert "@keydown.tab" in aside_tag

    def test_hamburger_has_ref_for_focus_restore(self, docente_eval_page):
        assert 'x-ref="hamburger"' in docente_eval_page

    def test_trap_focus_helper_present(self, docente_eval_page):
        assert "trapFocus" in docente_eval_page


# ══════════════════════════════════════════════════════════════════════════════
# P3 — Tables & grids
# ══════════════════════════════════════════════════════════════════════════════


class TestTableOverflowWrapper:

    def test_gestionar_evaluaciones_table_wrapped(self, docente_eval_page):
        overflow_idx = docente_eval_page.find("overflow-x-auto")
        table_idx = docente_eval_page.find("<table")
        assert overflow_idx != -1, "overflow-x-auto wrapper not found"
        assert table_idx != -1, "<table> not found"
        assert overflow_idx < table_idx


class TestGridMobileCollapse:

    def test_no_bare_grid_cols_in_dashboard_rendimiento(self, dashboard_rendimiento_page):
        assert _bare_grid_cols(dashboard_rendimiento_page) == []

    def test_grid_cols_1_present_in_dashboard_rendimiento(self, dashboard_rendimiento_page):
        assert "grid-cols-1" in dashboard_rendimiento_page

    def test_no_bare_grid_cols_in_editar_evaluacion(self, editar_evaluacion_page):
        assert _bare_grid_cols(editar_evaluacion_page) == []

    def test_no_bare_grid_cols_in_confirm_create_modal(self, usuario_create_page):
        assert _bare_grid_cols(usuario_create_page) == []
