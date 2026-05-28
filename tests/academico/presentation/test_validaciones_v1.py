"""
Integration tests for V1 (max asignaturas únicas por periodo según licencia).

Covers the 3 adapter call sites for `validar_max_asignaturas_por_periodo`:
- ParaleloForm.clean() (single create + edit-mode dedup with self.instance.pk excluded)
- ParaleloLoteForm.clean_asignaturas() (bulk — no exclude, always new)
- ParaleloSerializer.validate() (single create + edit-mode dedup)

The critical scenario is **edit-mode dedup at limit**: an existing paralelo whose
asignatura is already in `existentes` must remain valid because the adapter
excludes `self.instance.pk` from the existentes queryset.
"""

import datetime

import pytest

from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario


@pytest.fixture
def tipo_licencia_e():
    tl, _ = TipoLicencia.objects.get_or_create(
        codigo="E",
        defaults={
            "nombre": "Licencia E",
            "duracion_meses": 6,
            "num_asignaturas": 5,
            "activo": True,
        },
    )
    # Force num_asignaturas=5 even if a seed/migration created the row with a different value.
    if tl.num_asignaturas != 5:
        tl.num_asignaturas = 5
        tl.save(update_fields=["num_asignaturas"])
    return tl


@pytest.fixture
def docente():
    return Usuario.objects.create_user(
        username="docente_v1",
        email="docente_v1@test.com",
        password="testpass123",
        rol="docente",
    )


@pytest.fixture
def periodo_activo(tipo_licencia_e):
    return Periodo.objects.create(
        nombre="Periodo V1 Test",
        tipo_licencia=tipo_licencia_e,
        fecha_inicio=datetime.date(2026, 1, 1),
        fecha_fin=datetime.date(2026, 6, 30),
        activo=True,
    )


def _crear_asignatura(codigo: str, tipo_licencia: TipoLicencia) -> Asignatura:
    a = Asignatura.objects.create(nombre=f"Asig {codigo}", codigo=codigo, descripcion="")
    AsignaturaLicencia.objects.create(
        asignatura=a, tipo_licencia=tipo_licencia, horas_lectivas=20
    )
    return a


def _seed_paralelos(periodo, tipo_licencia, asignaturas, docente, prefix="P"):
    """Crea un Paralelo por cada asignatura en el (periodo, tipo_licencia)."""
    paralelos = []
    for idx, asig in enumerate(asignaturas):
        p = Paralelo.objects.create(
            periodo=periodo,
            tipo_licencia=tipo_licencia,
            asignatura=asig,
            nombre=f"{prefix}{idx}",
            docente=docente,
            capacidad_maxima=30,
        )
        paralelos.append(p)
    return paralelos


@pytest.mark.django_db
class TestParaleloFormV1MaxAsignaturas:
    """ParaleloForm enforces V1 via domain service with self.instance.pk exclusion."""

    def _form_data(self, periodo, tipo_licencia, asignatura, docente, nombre="A"):
        return {
            "periodo": periodo.pk,
            "tipo_licencia": tipo_licencia.pk,
            "asignatura": asignatura.pk,
            "nombre": nombre,
            "docente": docente.pk,
            "capacidad_maxima": 30,
        }

    def test_single_create_supera_limite_es_rechazado(
        self, periodo_activo, tipo_licencia_e, docente
    ):
        """Con 5 asignaturas ya ocupadas (limite=5), crear con una NUEVA falla."""
        from apps.academico.presentation.forms import ParaleloForm

        existentes = [_crear_asignatura(f"V1F-{i:03d}", tipo_licencia_e) for i in range(5)]
        _seed_paralelos(periodo_activo, tipo_licencia_e, existentes, docente)

        nueva = _crear_asignatura("V1F-NEW", tipo_licencia_e)
        form = ParaleloForm(
            data=self._form_data(periodo_activo, tipo_licencia_e, nueva, docente, nombre="X")
        )
        assert form.is_valid() is False
        assert "asignatura" in form.errors
        assert "permite máximo 5 asignaturas" in str(form.errors["asignatura"])

    def test_edit_mismo_paralelo_en_el_limite_dedup_es_valido(
        self, periodo_activo, tipo_licencia_e, docente
    ):
        """Estando al límite (5/5), editar un paralelo manteniendo su misma
        asignatura debe seguir siendo válido (instance.pk excluido de existentes)."""
        from apps.academico.presentation.forms import ParaleloForm

        existentes = [_crear_asignatura(f"V1F-E{i:03d}", tipo_licencia_e) for i in range(5)]
        paralelos = _seed_paralelos(
            periodo_activo, tipo_licencia_e, existentes, docente, prefix="EX"
        )
        target = paralelos[2]  # uno de los 5 al límite

        # Editar manteniendo MISMA asignatura → debe ser válido (dedup vía exclude pk)
        form = ParaleloForm(
            instance=target,
            data=self._form_data(
                periodo_activo, tipo_licencia_e, target.asignatura, docente, nombre="EX2-MOD"
            ),
        )
        assert form.is_valid() is True, form.errors


@pytest.mark.django_db
class TestParaleloLoteFormV1MaxAsignaturas:
    """ParaleloLoteForm enforces V1 via domain service (no exclude — bulk is always new)."""

    def _lote_data(self, periodo, tipo_licencia, asignaturas_ids, docente):
        return {
            "periodo": periodo.pk,
            "tipo_licencia": tipo_licencia.pk,
            "asignaturas": asignaturas_ids,
            "nombre": "L",
            "docente": docente.pk,
            "capacidad_maxima": 30,
        }

    def test_lote_que_cruza_el_limite_es_rechazado(
        self, periodo_activo, tipo_licencia_e, docente
    ):
        """existentes=3 + lote de 3 nuevas (todas distintas) → union=6 > 5 → falla."""
        from apps.academico.presentation.forms import ParaleloLoteForm

        existentes = [_crear_asignatura(f"V1L-{i:03d}", tipo_licencia_e) for i in range(3)]
        _seed_paralelos(periodo_activo, tipo_licencia_e, existentes, docente)

        nuevas = [_crear_asignatura(f"V1L-N{i:03d}", tipo_licencia_e) for i in range(3)]
        form = ParaleloLoteForm(
            data=self._lote_data(
                periodo_activo, tipo_licencia_e, [a.pk for a in nuevas], docente
            )
        )
        assert form.is_valid() is False
        # Error puede estar en 'asignaturas' (clean_asignaturas) o non-field; aceptamos ambos.
        errors_text = str(form.errors)
        assert "permite máximo 5 asignaturas" in errors_text

    def test_lote_que_completa_exacto_el_limite_es_valido(
        self, periodo_activo, tipo_licencia_e, docente
    ):
        """existentes=3 + lote de 2 nuevas → union=5 = limite → passes."""
        from apps.academico.presentation.forms import ParaleloLoteForm

        existentes = [_crear_asignatura(f"V1L-OK{i:03d}", tipo_licencia_e) for i in range(3)]
        _seed_paralelos(periodo_activo, tipo_licencia_e, existentes, docente)

        nuevas = [_crear_asignatura(f"V1L-OKN{i:03d}", tipo_licencia_e) for i in range(2)]
        form = ParaleloLoteForm(
            data=self._lote_data(
                periodo_activo, tipo_licencia_e, [a.pk for a in nuevas], docente
            )
        )
        assert form.is_valid() is True, form.errors


@pytest.mark.django_db
class TestParaleloSerializerV1MaxAsignaturas:
    """ParaleloSerializer enforces V1 via domain service, with self.instance.pk exclusion on update."""

    def _ser_data(self, periodo, tipo_licencia, asignatura, docente, nombre="A"):
        return {
            "periodo": periodo.pk,
            "tipo_licencia": tipo_licencia.pk,
            "asignatura": asignatura.pk,
            "nombre": nombre,
            "docente": docente.pk,
            "capacidad_maxima": 30,
        }

    def test_create_supera_limite_es_rechazado(
        self, periodo_activo, tipo_licencia_e, docente
    ):
        from apps.academico.presentation.serializers import ParaleloSerializer

        existentes = [_crear_asignatura(f"V1S-{i:03d}", tipo_licencia_e) for i in range(5)]
        _seed_paralelos(periodo_activo, tipo_licencia_e, existentes, docente)

        nueva = _crear_asignatura("V1S-NEW", tipo_licencia_e)
        serializer = ParaleloSerializer(
            data=self._ser_data(periodo_activo, tipo_licencia_e, nueva, docente, nombre="Z")
        )
        assert serializer.is_valid() is False
        assert "asignatura" in serializer.errors
        assert "permite máximo 5 asignaturas" in str(serializer.errors["asignatura"])

    def test_update_misma_asignatura_en_el_limite_dedup_es_valido(
        self, periodo_activo, tipo_licencia_e, docente
    ):
        """Edición de paralelo existente manteniendo su asignatura (limite 5, existentes=5)."""
        from apps.academico.presentation.serializers import ParaleloSerializer

        existentes = [_crear_asignatura(f"V1S-E{i:03d}", tipo_licencia_e) for i in range(5)]
        paralelos = _seed_paralelos(
            periodo_activo, tipo_licencia_e, existentes, docente, prefix="SU"
        )
        target = paralelos[1]

        serializer = ParaleloSerializer(
            instance=target,
            data=self._ser_data(
                periodo_activo,
                tipo_licencia_e,
                target.asignatura,
                docente,
                nombre="SU1-MOD",
            ),
        )
        assert serializer.is_valid() is True, serializer.errors
