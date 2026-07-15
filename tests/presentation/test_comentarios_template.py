"""Guard: ningún template usa comentarios ``{# ... #}`` multilínea.

Django solo reconoce ``{# #}`` cuando abre y cierra en la MISMA línea (su
``tag_re`` no compila con ``re.DOTALL``). Un ``{# #}`` que abarca varias líneas
no se trata como comentario: se renderiza como texto literal y termina visible
en la página. Para comentarios de varias líneas hay que usar
``{% comment %}...{% endcomment %}``, que el motor sí elimina server-side.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings


TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"

# {# ... #} con al menos un salto de línea entre los delimitadores.
_COMENTARIO_MULTILINEA = re.compile(r"\{#(?:(?!#\}).)*?\n(?:(?!#\}).)*?#\}", re.DOTALL)


@pytest.mark.parametrize(
    "plantilla",
    sorted(TEMPLATES_DIR.rglob("*.html")),
    ids=lambda p: p.name,
)
def test_sin_comentarios_django_multilinea(plantilla):
    fuente = plantilla.read_text(encoding="utf-8")

    hallazgos = _COMENTARIO_MULTILINEA.findall(fuente)

    assert not hallazgos, (
        f"{plantilla.relative_to(TEMPLATES_DIR)} usa un comentario {{# #}} "
        "multilínea, que Django renderiza como texto literal. Usá "
        "{% comment %}...{% endcomment %} para comentarios de varias líneas."
    )
