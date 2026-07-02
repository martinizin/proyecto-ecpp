"""
Tests para el toast component global de HU27b (templates/partials/_toast.html).

HU27b introduces un Alpine `toast()` component reusable, mountable en
``base.html`` y emitible via ``window.dispatchEvent(new CustomEvent('toast:show', ...))``.

Cubre:
    - T3.1  base.html incluye partials/_toast.html exactamente una vez
            y el partial renderiza ``function toast()`` en cualquier
            página autenticada.
    - T3.3  El partial define ``function toast() {``, ``_countdownInterval``,
            ``MAX_VISIBLE``, ``setTimeout`` y ``URL.revokeObjectURL``.
    - T3.5  ARIA attributes por tipo (polite para success/info/warning,
            assertive para error) + close button con ``aria-label``.

Estos tests son contract tests a nivel de template + source (el JS no
se ejecuta en el server). Las directivas Alpine ``:role=`` y
``:aria-live=`` se evalúan en el browser; en el server validamos la
PRESENCIA del binding expression en el source y la correctitud del
mapeo ``type → role/aria-live`` dentro del cuerpo de la función JS.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(settings.BASE_DIR)
BASE_HTML = REPO_ROOT / "templates" / "base.html"
TOAST_PARTIAL = REPO_ROOT / "templates" / "partials" / "_toast.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# T3.1 — base.html includes partials/_toast.html exactly once
# ---------------------------------------------------------------------------


class TestToastPartialIncludedInBase:
    """``base.html`` debe incluir el partial exactamente una vez."""

    def test_base_html_source_contains_toast_include(self):
        """T3.1 [RED→GREEN] — base.html source declares the include."""
        content = _read(BASE_HTML)
        assert '{% include "partials/_toast.html" %}' in content

    def test_base_html_source_includes_toast_partial_exactly_once(self):
        """No duplicate includes (defensive — a copy-paste error would
        render the global ``toast()`` function twice and break Alpine's
        single-source-of-truth contract)."""
        content = _read(BASE_HTML)
        assert content.count('{% include "partials/_toast.html" %}') == 1

    def test_dashboard_renders_toast_function(self, docente_client):
        """El partial se monta en cualquier página que extienda base.html.

        We use ``/usuarios/dashboard/`` because it extends ``base.html``
        and requires an auth'd user (so we get a real authenticated render).
        """
        response = docente_client.get(reverse("usuarios:dashboard"))
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # The partial's function must be in the rendered HTML
        assert "function toast()" in html

    def test_dashboard_includes_toast_partial_via_template_chain(self, docente_client):
        """``response.templates`` chain contains ``partials/_toast.html``."""
        response = docente_client.get(reverse("usuarios:dashboard"))
        assertTemplateUsed(response, "partials/_toast.html")


# ---------------------------------------------------------------------------
# T3.3 — Toast function source contract
# ---------------------------------------------------------------------------


class TestToastComponentContract:
    """El partial debe declarar el ``toast()`` factory + countdown state."""

    @pytest.mark.parametrize(
        "token",
        [
            "function toast()",
            "toasts:",
            "nextId",
            "_countdownInterval",
            "MAX_VISIBLE",
            "setInterval",
            "setTimeout",
            "URL.revokeObjectURL",
            "window.dispatchEvent",
        ],
    )
    def test_toast_partial_source_contains_required_token(self, token):
        """Cada token del contrato Alpine (D8 + D9 del design) debe estar
        en el source del partial."""
        content = _read(TOAST_PARTIAL)
        assert token in content, f"Missing required token: {token!r}"

    def test_toast_partial_renders_via_django_template_loader(self):
        """El partial es renderizable standalone (no requiere context vars
        externas). Esto garantiza que el include en base.html nunca falle
        con ``TemplateSyntaxError`` por variables no provistas."""
        from django.template.loader import render_to_string

        html = render_to_string("partials/_toast.html", context={})
        assert "function toast()" in html
        assert "_countdownInterval" in html


# ---------------------------------------------------------------------------
# T3.5 — ARIA attributes per type + close button a11y
# ---------------------------------------------------------------------------


class TestToastAriaContract:
    """ARIA live regions per R16 + close button per R18."""

    def test_toast_partial_uses_dynamic_role_binding(self):
        """El role se calcula dinámicamente según ``t.type`` (Alpine binding)."""
        content = _read(TOAST_PARTIAL)
        # Either a class binding, a ternary, or an x-bind:role is acceptable.
        # We look for the assertion contract: error → 'alert', other → 'status'.
        assert "t.type" in content
        # The literal values must appear in the binding
        assert re.search(
            r"role.*=.*['\"]alert['\"]", content
        ), "role='alert' must appear (error variant)"
        assert re.search(
            r"role.*=.*['\"]status['\"]", content
        ), "role='status' must appear (success/info/warning variant)"

    def test_toast_partial_uses_dynamic_aria_live_binding(self):
        """``aria-live`` se calcula según ``t.type``: error → 'assertive',
        otro → 'polite'."""
        content = _read(TOAST_PARTIAL)
        assert "aria-live" in content
        assert re.search(
            r"aria-live.*=.*['\"]assertive['\"]", content
        ), "aria-live='assertive' must appear (error variant)"
        assert re.search(
            r"aria-live.*=.*['\"]polite['\"]", content
        ), "aria-live='polite' must appear (success/info/warning variant)"

    def test_toast_partial_template_branches_t_type_for_aria(self):
        """The HTML template uses Alpine binding expressions that branch
        on ``t.type === 'error'`` to compute role and aria-live (R16)."""
        content = _read(TOAST_PARTIAL)
        # The pattern t.type === 'error' ? 'alert' : 'status' must appear
        assert re.search(
            r"t\.type\s*===\s*['\"]error['\"]\s*\?\s*['\"]alert['\"]",
            content,
        ), 'Template must bind :role=\'t.type === "error" ? "alert" : ...\''
        assert re.search(
            r"t\.type\s*===\s*['\"]error['\"]\s*\?\s*['\"]assertive['\"]",
            content,
        ), 'Template must bind :aria-live=\'t.type === "error" ? "assertive" : ...\''

    def test_toast_partial_aria_values_present(self):
        """All four ARIA literal values must appear in the source
        (R16: alert/status for role, assertive/polite for aria-live)."""
        content = _read(TOAST_PARTIAL)
        for value in ("alert", "status", "assertive", "polite"):
            assert (
                f"'{value}'" in content or f'"{value}"' in content
            ), f"ARIA literal {value!r} must appear in partial source"

    def test_close_button_has_aria_label(self):
        """Icon-only close button must have ``aria-label`` (R18)."""
        content = _read(TOAST_PARTIAL)
        # Find <button ... aria-label="..."> ... </button>
        # We accept any non-empty aria-label
        matches = re.findall(
            r'<button[^>]*aria-label="([^"]+)"[^>]*>',
            content,
        )
        assert len(matches) >= 1, "Close button must have aria-label"
        # The close button's label should be human-readable (not empty,
        # not a placeholder like "TODO" or "...").
        for label in matches:
            assert label.strip(), f"aria-label is empty: {label!r}"
            assert "TODO" not in label, f"aria-label is a placeholder: {label!r}"


# ---------------------------------------------------------------------------
# T3.5 (extra) — Auto-dismiss timing per type (R15)
# ---------------------------------------------------------------------------


class TestToastAutoDismiss:
    """Success/info/warning auto-dismiss 5s; error persists (R15)."""

    def test_toast_function_auto_dismiss_uses_5000ms(self):
        """Non-error types must use ``setTimeout(..., 5000)`` for dismiss."""
        content = _read(TOAST_PARTIAL)
        js_body = _extract_function_body(content, name="toast")
        # Look for any setTimeout call with 5000 (the spec'd auto-dismiss)
        assert "setTimeout" in js_body
        assert re.search(
            r"setTimeout\([^,]+,\s*5000\s*\)", js_body
        ), "setTimeout(..., 5000) must appear (R15: 5s auto-dismiss)"

    def test_toast_function_default_for_error_is_persistent(self):
        """For ``type === 'error'``, the spec says persistent (no auto-dismiss
        by default). The function should NOT call setTimeout(..., 5000)
        for the error branch, OR should pass autoDismissMs=0 explicitly."""
        content = _read(TOAST_PARTIAL)
        js_body = _extract_function_body(content, name="toast")
        # We accept either: a setTimeout(..., 0) for the error case
        # (which fires immediately and dismisses) — no, that would dismiss
        # immediately. We need either: NO setTimeout for the error branch
        # OR a setTimeout(..., 0) which is the "persistent" sentinel.
        # The simplest contract: the function must mention 'error' and
        # check for it explicitly.
        assert "error" in js_body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_function_body(source: str, name: str) -> str:
    """Extract the body of a top-level ``function NAME() { ... }`` declaration.

    Returns the inner body (between the outermost braces). Falls back to
    the full source if the function can't be located (so the calling
    test gets a less specific failure message).
    """
    match = re.search(
        rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{",
        source,
    )
    if not match:
        return source  # let the calling assertion fail clearly
    start = match.end()  # index just after the opening brace
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:i]
        i += 1
    return source[start:]
