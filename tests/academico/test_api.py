"""
DRF APIClient tests for Academico API endpoints.

Tests: CRUD, IsInspector permission, filters, pagination, /api/periodos/activo/.
Refs: AC-PER-06, AC-PER-07, AC-CAT-05, AC-CAT-07
"""

import datetime

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.academico.infrastructure.models import (
    Asignatura,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario


# =============================================================================
# Helpers
# =============================================================================


def _make_inspector():
    return Usuario.objects.create_user(
        username="inspector_api",
        email="inspector@api.com",
        password="Test123!",
        first_name="Carlos",
        last_name="Lopez",
        rol="inspector",
    )


def _make_docente():
    return Usuario.objects.create_user(
        username="docente_api",
        email="docente@api.com",
        password="Test123!",
        first_name="Maria",
        last_name="Garcia",
        rol="docente",
    )


def _make_estudiante():
    return Usuario.objects.create_user(
        username="estudiante_api",
        email="estudiante@api.com",
        password="Test123!",
        first_name="Juan",
        last_name="Perez",
        rol="estudiante",
    )


def _make_tipo_licencia(**kwargs):
    defaults = {
        "nombre": "Conducción",
        "codigo": "C",
        "duracion_meses": 6,
        "num_asignaturas": 5,
        "activo": True,
    }
    defaults.update(kwargs)
    return TipoLicencia.objects.create(**defaults)


def _make_periodo(creado_por=None, **kwargs):
    defaults = {
        "nombre": "2026-A",
        "fecha_inicio": datetime.date(2026, 3, 1),
        "fecha_fin": datetime.date(2026, 7, 31),
        "activo": True,
    }
    defaults.update(kwargs)
    if creado_por:
        defaults["creado_por"] = creado_por
    return Periodo.objects.create(**defaults)


def _make_asignatura(**kwargs):
    defaults = {
        "nombre": "Legislación de Tránsito",
        "codigo": "LEG-001",
        "descripcion": "Descripción de prueba",
        "horas_lectivas": 40,
    }
    defaults.update(kwargs)
    return Asignatura.objects.create(**defaults)


# =============================================================================
# TestPeriodoAPI — 9 tests
# =============================================================================


@pytest.mark.django_db
class TestPeriodoAPI:
    """Tests for /academico/api/periodos/ endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.inspector = _make_inspector()
        self.docente = _make_docente()

    # --- List ---

    def test_list_periodos_authenticated(self):
        """GET /api/periodos/ with authenticated user → 200, returns results list."""
        self.client.force_authenticate(user=self.inspector)
        _make_periodo(creado_por=self.inspector)

        url = reverse("academico:api-periodo-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1

    def test_list_periodos_anonymous(self):
        """GET /api/periodos/ without auth → 403."""
        url = reverse("academico:api-periodo-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    # --- Create ---

    def test_create_periodo_inspector(self):
        """POST /api/periodos/ as inspector → 201, creates in DB, creado_por set."""
        self.client.force_authenticate(user=self.inspector)
        url = reverse("academico:api-periodo-list")
        data = {
            "nombre": "2026-B",
            "fecha_inicio": "2026-09-01",
            "fecha_fin": "2027-02-28",
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Periodo.objects.filter(nombre="2026-B").exists()
        periodo = Periodo.objects.get(nombre="2026-B")
        assert periodo.creado_por == self.inspector

    def test_create_periodo_docente_forbidden(self):
        """POST /api/periodos/ as docente → 403."""
        self.client.force_authenticate(user=self.docente)
        url = reverse("academico:api-periodo-list")
        data = {
            "nombre": "2026-B",
            "fecha_inicio": "2026-09-01",
            "fecha_fin": "2027-02-28",
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    # --- Retrieve ---

    def test_retrieve_periodo(self):
        """GET /api/periodos/{id}/ → 200, returns correct data."""
        self.client.force_authenticate(user=self.inspector)
        periodo = _make_periodo(creado_por=self.inspector, nombre="2026-C")

        url = reverse("academico:api-periodo-detail", args=[periodo.pk])
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["nombre"] == "2026-C"
        assert response.data["id"] == periodo.pk

    # --- Update ---

    def test_update_periodo_inspector(self):
        """PATCH /api/periodos/{id}/ as inspector → 200, updates in DB."""
        self.client.force_authenticate(user=self.inspector)
        periodo = _make_periodo(creado_por=self.inspector)

        url = reverse("academico:api-periodo-detail", args=[periodo.pk])
        response = self.client.patch(
            url, {"nombre": "2026-A-Modificado"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        periodo.refresh_from_db()
        assert periodo.nombre == "2026-A-Modificado"

    # --- Delete ---

    def test_delete_periodo_inspector(self):
        """DELETE /api/periodos/{id}/ as inspector → 204."""
        self.client.force_authenticate(user=self.inspector)
        periodo = _make_periodo(creado_por=self.inspector)

        url = reverse("academico:api-periodo-detail", args=[periodo.pk])
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Periodo.objects.filter(pk=periodo.pk).exists()

    # --- Activo endpoint ---

    def test_activo_endpoint_exists(self):
        """GET /api/periodos/activo/ with active period → 200 + data."""
        self.client.force_authenticate(user=self.inspector)
        periodo = _make_periodo(creado_por=self.inspector, activo=True)

        url = reverse("academico:api-periodo-activo")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == periodo.pk
        assert response.data["activo"] is True

    def test_activo_endpoint_no_active(self):
        """GET /api/periodos/activo/ without active period → 404."""
        self.client.force_authenticate(user=self.inspector)
        _make_periodo(creado_por=self.inspector, activo=False)

        url = reverse("academico:api-periodo-activo")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestTipoLicenciaAPI — 3 tests
# =============================================================================


@pytest.mark.django_db
class TestTipoLicenciaAPI:
    """Tests for /academico/api/tipos-licencia/ endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.inspector = _make_inspector()
        self.client.force_authenticate(user=self.inspector)

    def test_list_tipos_licencia(self):
        """GET /api/tipos-licencia/ → 200, returns only active types."""
        _make_tipo_licencia(nombre="Conducción", codigo="C", activo=True)
        _make_tipo_licencia(nombre="Inactiva", codigo="X", activo=False)

        url = reverse("academico:api-tipo-licencia-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        codigos = [item["codigo"] for item in response.data["results"]]
        assert "C" in codigos
        assert "X" not in codigos

    def test_retrieve_tipo_licencia(self):
        """GET /api/tipos-licencia/{id}/ → 200."""
        tl = _make_tipo_licencia()

        url = reverse("academico:api-tipo-licencia-detail", args=[tl.pk])
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["codigo"] == "C"

    def test_create_tipo_licencia_not_allowed(self):
        """POST /api/tipos-licencia/ → 405 (read-only ViewSet)."""
        url = reverse("academico:api-tipo-licencia-list")
        data = {
            "nombre": "Especial",
            "codigo": "ESP",
            "duracion_meses": 12,
            "num_asignaturas": 3,
            "activo": True,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# =============================================================================
# TestAsignaturaAPI — 5 tests
# =============================================================================


@pytest.mark.django_db
class TestAsignaturaAPI:
    """Tests for /academico/api/asignaturas/ endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.inspector = _make_inspector()
        self.estudiante = _make_estudiante()

    def test_list_asignaturas(self):
        """GET /api/asignaturas/ → 200, returns results."""
        self.client.force_authenticate(user=self.inspector)
        _make_asignatura()

        url = reverse("academico:api-asignatura-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1

    def test_create_asignatura_inspector(self):
        """POST /api/asignaturas/ as inspector → 201 with tipos_licencia IDs."""
        self.client.force_authenticate(user=self.inspector)
        tl1 = _make_tipo_licencia(nombre="Conducción", codigo="C")
        tl2 = _make_tipo_licencia(nombre="Educación", codigo="E")

        url = reverse("academico:api-asignatura-list")
        data = {
            "nombre": "Legislación de Tránsito",
            "codigo": "LEG-001",
            "descripcion": "Curso de leyes",
            "horas_lectivas": 40,
            "tipos_licencia": [tl1.pk, tl2.pk],
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        asig = Asignatura.objects.get(codigo="LEG-001")
        assert asig.tipos_licencia.count() == 2

    def test_create_asignatura_estudiante_forbidden(self):
        """POST /api/asignaturas/ as estudiante → 403."""
        self.client.force_authenticate(user=self.estudiante)
        tl = _make_tipo_licencia()

        url = reverse("academico:api-asignatura-list")
        data = {
            "nombre": "Legislación",
            "codigo": "LEG-002",
            "horas_lectivas": 40,
            "tipos_licencia": [tl.pk],
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_by_tipo_licencia(self):
        """GET /api/asignaturas/?tipo_licencia={id} → returns only matching."""
        self.client.force_authenticate(user=self.inspector)
        tl_c = _make_tipo_licencia(nombre="Conducción", codigo="C")
        tl_e = _make_tipo_licencia(nombre="Educación", codigo="E")

        asig_c = _make_asignatura(nombre="Solo Conducción", codigo="SC-001")
        asig_c.tipos_licencia.add(tl_c)

        asig_e = _make_asignatura(nombre="Solo Educación", codigo="SE-001")
        asig_e.tipos_licencia.add(tl_e)

        url = reverse("academico:api-asignatura-list")
        response = self.client.get(url, {"tipo_licencia": tl_c.pk})

        assert response.status_code == status.HTTP_200_OK
        codigos = [item["codigo"] for item in response.data["results"]]
        assert "SC-001" in codigos
        assert "SE-001" not in codigos

    def test_response_includes_tipos_licencia_detail(self):
        """GET response has tipos_licencia_detail as nested objects."""
        self.client.force_authenticate(user=self.inspector)
        tl = _make_tipo_licencia(nombre="Conducción", codigo="C")
        asig = _make_asignatura()
        asig.tipos_licencia.add(tl)

        url = reverse("academico:api-asignatura-detail", args=[asig.pk])
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "tipos_licencia_detail" in response.data
        detail = response.data["tipos_licencia_detail"]
        assert len(detail) == 1
        assert detail[0]["codigo"] == "C"
        assert detail[0]["nombre"] == "Conducción"


# =============================================================================
# TestParaleloAPI — 6 tests
# =============================================================================


@pytest.mark.django_db
class TestParaleloAPI:
    """Tests for /academico/api/paralelos/ endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.inspector = _make_inspector()
        self.docente = _make_docente()
        self.tipo_licencia = _make_tipo_licencia()
        self.periodo = _make_periodo(creado_por=self.inspector)
        self.asignatura = _make_asignatura()
        self.asignatura.tipos_licencia.add(self.tipo_licencia)

    def _paralelo_data(self, **overrides):
        """Default payload for creating a Paralelo."""
        data = {
            "asignatura": self.asignatura.pk,
            "periodo": self.periodo.pk,
            "tipo_licencia": self.tipo_licencia.pk,
            "docente": self.docente.pk,
            "nombre": "A",
            "horario": "Lun-Mie 08:00-10:00",
            "capacidad_maxima": 30,
        }
        data.update(overrides)
        return data

    def test_list_paralelos(self):
        """GET /api/paralelos/ → 200, returns results."""
        self.client.force_authenticate(user=self.inspector)
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            horario="Lun-Mie 08:00-10:00",
            capacidad_maxima=30,
        )

        url = reverse("academico:api-paralelo-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1

    def test_create_paralelo_inspector(self):
        """POST /api/paralelos/ as inspector → 201."""
        self.client.force_authenticate(user=self.inspector)
        url = reverse("academico:api-paralelo-list")

        response = self.client.post(url, self._paralelo_data(), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Paralelo.objects.filter(nombre="A").exists()

    def test_create_paralelo_docente_forbidden(self):
        """POST /api/paralelos/ as docente → 403."""
        self.client.force_authenticate(user=self.docente)
        url = reverse("academico:api-paralelo-list")

        response = self.client.post(url, self._paralelo_data(), format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_by_periodo(self):
        """GET /api/paralelos/?periodo={id} → returns only matching."""
        self.client.force_authenticate(user=self.inspector)
        periodo2 = _make_periodo(
            nombre="2026-B",
            fecha_inicio=datetime.date(2026, 9, 1),
            fecha_fin=datetime.date(2027, 2, 28),
            activo=False,
        )
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=periodo2,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="B",
            capacidad_maxima=30,
        )

        url = reverse("academico:api-paralelo-list")
        response = self.client.get(url, {"periodo": self.periodo.pk})

        assert response.status_code == status.HTTP_200_OK
        nombres = [item["nombre"] for item in response.data["results"]]
        assert "A" in nombres
        assert "B" not in nombres

    def test_filter_by_tipo_licencia(self):
        """GET /api/paralelos/?tipo_licencia={id} → returns only matching."""
        self.client.force_authenticate(user=self.inspector)
        tl2 = _make_tipo_licencia(nombre="Educación", codigo="E")
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=tl2,
            docente=self.docente,
            nombre="B",
            capacidad_maxima=30,
        )

        url = reverse("academico:api-paralelo-list")
        response = self.client.get(url, {"tipo_licencia": self.tipo_licencia.pk})

        assert response.status_code == status.HTTP_200_OK
        nombres = [item["nombre"] for item in response.data["results"]]
        assert "A" in nombres
        assert "B" not in nombres

    def test_response_includes_nested_names(self):
        """Response has asignatura_nombre, periodo_nombre, tipo_licencia_codigo, docente_nombre."""
        self.client.force_authenticate(user=self.inspector)
        paralelo = Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            horario="Lun 08:00",
            capacidad_maxima=30,
        )

        url = reverse("academico:api-paralelo-detail", args=[paralelo.pk])
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["asignatura_nombre"] == self.asignatura.nombre
        assert response.data["periodo_nombre"] == self.periodo.nombre
        assert response.data["tipo_licencia_codigo"] == self.tipo_licencia.codigo
        assert response.data["docente_nombre"] == self.docente.get_full_name()
