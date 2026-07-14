"""Guard: Alpine components must not be defined inside ``{% block extra_js %}``.

``base.html`` boosts navigation with htmx (``hx-target="#main-content"``), and
``extra_js`` renders OUTSIDE ``#main-content``. htmx only re-evaluates scripts
that live in the swapped content, so a component defined in ``extra_js`` is
never registered when the page is reached through a boosted link: the
``x-data="componente()"`` on the page then references an undefined function and
the whole Alpine component silently dies.

That is what broke the "Todos" checkbox in the attendance sheet (Issue 10) —
the individual checkboxes kept toggling because that is native browser
behaviour, so the failure looked like it only affected the global one.

The rule: page data (``json_script``) and the component ``<script>`` go inside
``{% block content %}``, using only ``function`` declarations (a top-level
``const``/``let`` would throw "already declared" on the second visit, since
htmx re-evaluates the script on every swap).
"""

import re
from pathlib import Path

import pytest
from django.conf import settings


TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"

_X_DATA_COMPONENTE = re.compile(r'x-data="\s*([a-zA-Z_$][\w$]*)\s*\(')
_INICIO_EXTRA_JS = "{% block extra_js %}"


def _plantillas():
    return sorted(TEMPLATES_DIR.rglob("*.html"))


def _componentes_definidos_en_extra_js(fuente: str) -> list[str]:
    """Component names used by x-data whose ``function`` sits inside extra_js."""
    inicio = fuente.find(_INICIO_EXTRA_JS)
    if inicio == -1:
        return []

    bloque_extra_js = fuente[inicio:]
    culpables = []
    for nombre in set(_X_DATA_COMPONENTE.findall(fuente)):
        definicion = re.compile(rf"function\s+{re.escape(nombre)}\s*\(")
        if definicion.search(bloque_extra_js):
            culpables.append(nombre)
    return sorted(culpables)


@pytest.mark.parametrize("plantilla", _plantillas(), ids=lambda p: p.name)
def test_componente_alpine_no_se_define_en_extra_js(plantilla):
    fuente = plantilla.read_text(encoding="utf-8")

    culpables = _componentes_definidos_en_extra_js(fuente)

    assert not culpables, (
        f"{plantilla.relative_to(TEMPLATES_DIR)} define {culpables} dentro de "
        "{% block extra_js %}, que queda fuera de #main-content y no se "
        "re-ejecuta en navegación boosted. Mové el <script> al bloque content."
    )
