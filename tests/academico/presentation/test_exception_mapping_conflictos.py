"""
Pruebas unitarias para la extensión de `exception_mapping` que serializa
los conflictos de horario hacia el payload DRF (HU21 QA V5).

RED phase (Task 0.1 SDD qa-academico-conflictos-horario-v5):
- `Conflicto` DTO aún no existe en `apps.academico.domain.services`.
- `ConflictoHorarioDocenteError` aún no existe en `apps.academico.domain.exceptions`.
- `to_drf` aún no inspecciona `exc.conflictos`.

Por lo tanto este archivo debe FALLAR en collection/import — comportamiento
esperado en RED estricta.
"""

from datetime import time

from rest_framework import serializers as drf_serializers

from apps.academico.domain.exceptions import ConflictoHorarioDocenteError
from apps.academico.domain.services import Conflicto
from apps.academico.presentation.exception_mapping import to_drf


def _build_conflictos() -> list[Conflicto]:
    """Construye una lista de 2 Conflicto para los assertions."""
    return [
        Conflicto(
            paralelo_id=12,
            paralelo_nombre="A",
            asignatura_codigo="MAT-101",
            asignatura_nombre="Matemáticas",
            dia_semana="lunes",
            dia_semana_label="Lunes",
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
        ),
        Conflicto(
            paralelo_id=13,
            paralelo_nombre="B",
            asignatura_codigo="FIS-201",
            asignatura_nombre="Física",
            dia_semana="martes",
            dia_semana_label="Martes",
            hora_inicio=time(14, 30),
            hora_fin=time(16, 0),
        ),
    ]


class TestToDrfConflictosPayload:
    """`to_drf` debe enriquecer el payload cuando `exc.conflictos` existe."""

    def test_to_drf_without_field_returns_detail_and_conflictos_list(self):
        conflictos = _build_conflictos()
        exc = ConflictoHorarioDocenteError(conflictos)

        result = to_drf(exc)

        assert isinstance(result, drf_serializers.ValidationError)
        detail = result.detail
        # El payload debe ser un dict con `detail` (mensaje) y `conflictos` (lista de dicts).
        assert "detail" in detail, f"falta clave 'detail' en payload: {detail!r}"
        assert "conflictos" in detail, f"falta clave 'conflictos' en payload: {detail!r}"
        assert isinstance(detail["conflictos"], list)
        assert len(detail["conflictos"]) == 2

    def test_to_drf_serializes_hora_inicio_and_hora_fin_as_isoformat_strings(self):
        conflictos = _build_conflictos()
        exc = ConflictoHorarioDocenteError(conflictos)

        result = to_drf(exc)

        primer_conflicto = result.detail["conflictos"][0]
        # `time.isoformat()` produce "HH:MM:SS" — son strings, no instancias time.
        assert isinstance(primer_conflicto["hora_inicio"], str)
        assert isinstance(primer_conflicto["hora_fin"], str)
        assert primer_conflicto["hora_inicio"] == "08:00:00"
        assert primer_conflicto["hora_fin"] == "10:00:00"

    def test_to_drf_conflictos_preserve_all_dto_fields(self):
        conflictos = _build_conflictos()
        exc = ConflictoHorarioDocenteError(conflictos)

        result = to_drf(exc)

        primer = result.detail["conflictos"][0]
        # Los 8 campos del DTO Conflicto deben estar presentes en el payload.
        assert primer["paralelo_id"] == 12
        assert primer["paralelo_nombre"] == "A"
        assert primer["asignatura_codigo"] == "MAT-101"
        assert primer["asignatura_nombre"] == "Matemáticas"
        assert primer["dia_semana"] == "lunes"
        assert primer["dia_semana_label"] == "Lunes"

    def test_to_drf_with_field_routes_payload_under_field_key(self):
        conflictos = _build_conflictos()
        exc = ConflictoHorarioDocenteError(conflictos)

        result = to_drf(exc, field="bloques")

        assert isinstance(result, drf_serializers.ValidationError)
        detail = result.detail
        # El payload completo (detail + conflictos) debe vivir bajo la clave del campo.
        assert "bloques" in detail
        payload = detail["bloques"]
        # DRF puede envolver el payload en una lista de un solo elemento o exponerlo
        # como dict directo; en ambos casos los datos quedan accesibles.
        if isinstance(payload, list):
            payload = payload[0]
        assert "detail" in payload
        assert "conflictos" in payload
        assert len(payload["conflictos"]) == 2
