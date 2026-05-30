"""
Integration tests for V3 (capacidad de paralelo) presentation layer.

Verifies that ParaleloForm, ParaleloLoteForm and ParaleloSerializer enforce
the [1, PARALELO_CAPACIDAD_MAXIMA=50] bound via the domain service.
"""

import pytest

from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario


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


@pytest.fixture
def docente():
    return Usuario.objects.create_user(
        username="docente_v3",
        email="docente_v3@test.com",
        password="testpass123",
        rol="docente",
    )


@pytest.fixture
def periodo_activo(tipo_licencia_c):
    import datetime

    return Periodo.objects.create(
        nombre="Periodo V3 Test",
        tipo_licencia=tipo_licencia_c,
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 6, 30),
        activo=True,
    )


@pytest.fixture
def asignatura_c(tipo_licencia_c):
    a = Asignatura.objects.create(
        nombre="Asig V3",
        codigo="V3-001",
        descripcion="",
    )
    AsignaturaLicencia.objects.create(
        asignatura=a, tipo_licencia=tipo_licencia_c, horas_lectivas=20
    )
    return a


@pytest.mark.django_db
class TestParaleloFormValidarCapacidad:
    """ParaleloForm rejects capacidad fuera de [1, 50] vía domain service."""

    def _base_data(self, periodo, tipo_licencia, asignatura, docente, capacidad):
        return {
            "periodo": periodo.pk,
            "tipo_licencia": tipo_licencia.pk,
            "asignatura": asignatura.pk,
            "nombre": "A",
            "docente": docente.pk,
            "capacidad_maxima": capacidad,
        }

    def test_capacidad_51_rechazada(self, periodo_activo, tipo_licencia_c, asignatura_c, docente):
        from apps.academico.presentation.forms import ParaleloForm

        form = ParaleloForm(
            data=self._base_data(periodo_activo, tipo_licencia_c, asignatura_c, docente, 51)
        )
        assert form.is_valid() is False
        assert "capacidad_maxima" in form.errors
        assert "entre 1 y 50" in str(form.errors["capacidad_maxima"])

    def test_capacidad_50_aceptada(self, periodo_activo, tipo_licencia_c, asignatura_c, docente):
        from apps.academico.presentation.forms import ParaleloForm

        form = ParaleloForm(
            data=self._base_data(periodo_activo, tipo_licencia_c, asignatura_c, docente, 50)
        )
        assert form.is_valid() is True, form.errors


@pytest.mark.django_db
class TestParaleloLoteFormCapacidadMaxima:
    """ParaleloLoteForm rejects capacidad > settings.PARALELO_CAPACIDAD_MAXIMA."""

    def test_capacidad_51_rechazada(self, periodo_activo, tipo_licencia_c, asignatura_c, docente):
        from apps.academico.presentation.forms import ParaleloLoteForm

        data = {
            "periodo": periodo_activo.pk,
            "tipo_licencia": tipo_licencia_c.pk,
            "asignaturas": [asignatura_c.pk],
            "nombre": "A",
            "docente": docente.pk,
            "capacidad_maxima": 51,
        }
        form = ParaleloLoteForm(data=data)
        assert form.is_valid() is False
        assert "capacidad_maxima" in form.errors


@pytest.mark.django_db
class TestParaleloSerializerValidarCapacidad:
    """ParaleloSerializer enforces V3 bounds via domain delegation."""

    def test_capacidad_51_retorna_error(
        self, periodo_activo, tipo_licencia_c, asignatura_c, docente
    ):
        from apps.academico.presentation.serializers import ParaleloSerializer

        data = {
            "periodo": periodo_activo.pk,
            "tipo_licencia": tipo_licencia_c.pk,
            "asignatura": asignatura_c.pk,
            "nombre": "A",
            "docente": docente.pk,
            "capacidad_maxima": 51,
        }
        serializer = ParaleloSerializer(data=data)
        assert serializer.is_valid() is False
        assert "capacidad_maxima" in serializer.errors
        assert "entre 1 y 50" in str(serializer.errors["capacidad_maxima"])

    def test_capacidad_50_es_valida(self, periodo_activo, tipo_licencia_c, asignatura_c, docente):
        from apps.academico.presentation.serializers import ParaleloSerializer

        data = {
            "periodo": periodo_activo.pk,
            "tipo_licencia": tipo_licencia_c.pk,
            "asignatura": asignatura_c.pk,
            "nombre": "A",
            "docente": docente.pk,
            "capacidad_maxima": 50,
        }
        serializer = ParaleloSerializer(data=data)
        assert serializer.is_valid() is True, serializer.errors
