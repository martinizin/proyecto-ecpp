"""
RED test (task 3.1) for `templates/academico/partials/conflicto_horario_error.html`.

Renders the partial in isolation with a fixture of 2 `Conflicto` DTOs and a
`mensaje` (str of the exception) and asserts:
  - Mensaje del exception se renderiza (str(exc)).
  - Markup accesible: role="alert" + aria-live.
  - Cada Conflicto se lista con paralelo_nombre, asignatura_codigo +
    asignatura_nombre, dia_semana_label y horas formateadas HH:MM.

El partial es server-side render puro (sin Alpine, sin JS). Tailwind 3.4.17
clases consistentes con `paralelo_form.html`.
"""

from __future__ import annotations

from datetime import time

import pytest
from django.template.loader import render_to_string

from apps.academico.domain.exceptions import ConflictoHorarioDocenteError
from apps.academico.domain.services import Conflicto


@pytest.fixture
def conflictos_fixture() -> list[Conflicto]:
    return [
        Conflicto(
            paralelo_id=1,
            paralelo_nombre="A",
            asignatura_codigo="MAT101",
            asignatura_nombre="Matematicas",
            dia_semana="lunes",
            dia_semana_label="Lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        ),
        Conflicto(
            paralelo_id=2,
            paralelo_nombre="B",
            asignatura_codigo="FIS201",
            asignatura_nombre="Fisica",
            dia_semana="martes",
            dia_semana_label="Martes",
            hora_inicio=time(14, 30),
            hora_fin=time(16, 30),
        ),
    ]


class TestPartialConflictoHorario:
    def test_partial_renderiza_mensaje_y_lista_conflictos(self, conflictos_fixture):
        exc = ConflictoHorarioDocenteError(conflictos_fixture)
        html = render_to_string(
            "academico/partials/conflicto_horario_error.html",
            {"conflictos": conflictos_fixture, "mensaje": str(exc)},
        )

        # Accesibilidad: role="alert" + aria-live
        assert 'role="alert"' in html
        assert "aria-live" in html

        # Mensaje del exception aparece (al menos parte estable)
        assert "Conflicto de horario" in html or "conflicto" in html.lower()

        # Datos de cada conflicto
        assert "MAT101" in html
        assert "Matematicas" in html
        assert "Lunes" in html
        assert "08:00" in html
        assert "10:00" in html

        assert "FIS201" in html
        assert "Fisica" in html
        assert "Martes" in html
        assert "14:30" in html
        assert "16:30" in html

        # Nombre de paralelo visible
        assert ">A<" in html or "Paralelo A" in html or " A " in html
        assert ">B<" in html or "Paralelo B" in html or " B " in html

    def test_partial_no_renderiza_nada_sin_conflictos(self):
        html = render_to_string(
            "academico/partials/conflicto_horario_error.html",
            {"conflictos": [], "mensaje": ""},
        )
        # Guard {% if conflictos %} → output vacío o sin role=alert
        assert 'role="alert"' not in html
