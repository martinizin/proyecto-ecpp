"""
Integration tests for V4 (duración de periodo 4-7 meses) presentation layer.

Verifies that PeriodoForm and PeriodoSerializer enforce the
[PERIODO_DURACION_MIN_MESES=4, PERIODO_DURACION_MAX_MESES=7] bound via the
domain service, with lenient month counting (trailing days bump up).

Existing fi < ff guard MUST keep working (no regression).
"""

import datetime

import pytest

from apps.academico.infrastructure.models import TipoLicencia


@pytest.fixture
def tipo_licencia_c():
    tl, _ = TipoLicencia.objects.get_or_create(
        codigo="C",
        defaults={
            "nombre": "Licenciatura en Ciencias",
            "duracion_meses": 48,
            "num_asignaturas": 5,
            "activo": True,
        },
    )
    return tl


def _form_data(tipo_licencia, fi, ff, nombre="Periodo V4 Test"):
    return {
        "nombre": nombre,
        "tipo_licencia": tipo_licencia.pk,
        "fecha_inicio": fi.isoformat(),
        "fecha_fin": ff.isoformat(),
    }


@pytest.mark.django_db
class TestPeriodoFormValidarDuracion:
    """PeriodoForm rejects duración fuera de [4, 7] meses (lenient)."""

    def test_duracion_3_meses_rechazada(self, tipo_licencia_c):
        from apps.academico.presentation.forms import PeriodoForm

        data = _form_data(
            tipo_licencia_c,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 4, 1),
        )
        form = PeriodoForm(data=data)
        assert form.is_valid() is False
        assert "fecha_fin" in form.errors
        assert "entre 4 y 7 meses" in str(form.errors["fecha_fin"])

    def test_duracion_4_meses_exactos_aceptada(self, tipo_licencia_c):
        from apps.academico.presentation.forms import PeriodoForm

        data = _form_data(
            tipo_licencia_c,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 5, 1),
        )
        form = PeriodoForm(data=data)
        assert form.is_valid() is True, form.errors

    def test_duracion_8_meses_rechazada_lenient(self, tipo_licencia_c):
        """7 months + 1 day → bump → 8 meses → INVALID."""
        from apps.academico.presentation.forms import PeriodoForm

        data = _form_data(
            tipo_licencia_c,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 8, 2),
        )
        form = PeriodoForm(data=data)
        assert form.is_valid() is False
        assert "fecha_fin" in form.errors
        assert "entre 4 y 7 meses" in str(form.errors["fecha_fin"])

    def test_fi_mayor_que_ff_sigue_rechazada_sin_regression(self, tipo_licencia_c):
        """Existing fi >= ff guard must keep working (no regression)."""
        from apps.academico.presentation.forms import PeriodoForm

        data = _form_data(
            tipo_licencia_c,
            datetime.date(2026, 5, 1),
            datetime.date(2026, 1, 1),
        )
        form = PeriodoForm(data=data)
        assert form.is_valid() is False
        # Non-field error from existing guard.
        assert any("anterior a la fecha de fin" in str(err) for err in form.errors.values())


@pytest.mark.django_db
class TestPeriodoSerializerValidarDuracion:
    """PeriodoSerializer mirrors V4 bounds via domain delegation."""

    def _data(self, tipo_licencia, fi, ff):
        return {
            "nombre": "Periodo V4 Serializer",
            "tipo_licencia": tipo_licencia.pk,
            "fecha_inicio": fi.isoformat(),
            "fecha_fin": ff.isoformat(),
        }

    def test_duracion_3_meses_retorna_error(self, tipo_licencia_c):
        from apps.academico.presentation.serializers import PeriodoSerializer

        data = self._data(
            tipo_licencia_c,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 4, 1),
        )
        serializer = PeriodoSerializer(data=data)
        assert serializer.is_valid() is False
        assert "fecha_fin" in serializer.errors
        assert "entre 4 y 7 meses" in str(serializer.errors["fecha_fin"])

    def test_duracion_4_meses_exactos_es_valida(self, tipo_licencia_c):
        from apps.academico.presentation.serializers import PeriodoSerializer

        data = self._data(
            tipo_licencia_c,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 5, 1),
        )
        serializer = PeriodoSerializer(data=data)
        assert serializer.is_valid() is True, serializer.errors
