"""
View tests for the Academico bounded context using Django test Client.

Tests: PeriodoListView, PeriodoCreateView, PeriodoUpdateView,
       AsignaturaListView, AsignaturaCreateView, AsignaturaUpdateView,
       ParaleloListView, ParaleloCreateView, ParaleloUpdateView,
       TipoLicenciaListView.
Role enforcement: all views require Inspector — non-inspectors get 403.
Refs: HU05, HU06, SCN-PER-01→04, SCN-CAT-01→10
"""

import datetime

import pytest
from django.test import Client
from django.urls import reverse

from apps.academico.infrastructure.models import (
    Asignatura,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.usuarios.infrastructure.models import Usuario

PASSWORD = "Test123!"


# =============================================================================
# Helpers
# =============================================================================


def _create_inspector() -> Usuario:
    return Usuario.objects.create_user(
        username="inspector_v",
        email="inspector@v.com",
        password=PASSWORD,
        first_name="Carlos",
        last_name="Lopez",
        rol="inspector",
        is_active=True,
    )


def _create_docente() -> Usuario:
    return Usuario.objects.create_user(
        username="docente_v",
        email="docente@v.com",
        password=PASSWORD,
        first_name="Maria",
        last_name="Garcia",
        rol="docente",
        is_active=True,
    )


def _create_estudiante() -> Usuario:
    return Usuario.objects.create_user(
        username="estudiante_v",
        email="estudiante@v.com",
        password=PASSWORD,
        first_name="Juan",
        last_name="Perez",
        rol="estudiante",
        is_active=True,
    )


def _create_tipo_licencia(**kwargs) -> TipoLicencia:
    defaults = {
        "nombre": "Conducción",
        "codigo": "C",
        "duracion_meses": 6,
        "num_asignaturas": 5,
        "activo": True,
    }
    defaults.update(kwargs)
    codigo = defaults.pop("codigo")
    obj, _ = TipoLicencia.objects.get_or_create(
        codigo=codigo, defaults=defaults,
    )
    for key, val in defaults.items():
        setattr(obj, key, val)
    obj.save()
    return obj


def _create_periodo(creado_por=None, **kwargs) -> Periodo:
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


def _create_asignatura(**kwargs) -> Asignatura:
    defaults = {
        "nombre": "Legislación de Tránsito",
        "codigo": "LEG-001",
        "descripcion": "Descripción de prueba",
        "horas_lectivas": 40,
    }
    defaults.update(kwargs)
    return Asignatura.objects.create(**defaults)


# =============================================================================
# TestPeriodoViews — 7 tests
# =============================================================================


@pytest.mark.django_db
class TestPeriodoViews:
    """View tests for academic period CRUD (HU05)."""

    def setup_method(self):
        self.client = Client()
        self.inspector = _create_inspector()
        self.client.force_login(self.inspector)

    # --- List ---

    def test_list_periodos_inspector(self):
        """GET /academico/periodos/ as inspector → 200, correct template and context."""
        _create_periodo(creado_por=self.inspector)

        url = reverse("academico:periodo_list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "academico/periodo_list.html" in [t.name for t in response.templates]
        assert "periodos" in response.context

    def test_list_periodos_docente_forbidden(self):
        """GET /academico/periodos/ as docente → 403."""
        docente_client = Client()
        docente = _create_docente()
        docente_client.force_login(docente)

        url = reverse("academico:periodo_list")
        response = docente_client.get(url)

        assert response.status_code == 403

    def test_list_periodos_anonymous_redirect(self):
        """GET /academico/periodos/ anonymous → redirect to login."""
        anonymous_client = Client()

        url = reverse("academico:periodo_list")
        response = anonymous_client.get(url)

        assert response.status_code == 302
        assert "/usuarios/login/" in response.url

    # --- Create ---

    def test_create_periodo_get(self):
        """GET /academico/periodos/crear/ → 200 with form in context."""
        url = reverse("academico:periodo_create")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_create_periodo_post_exitoso(self):
        """POST valid data → redirects to periodo_list, period created in DB."""
        url = reverse("academico:periodo_create")
        data = {
            "nombre": "2026-B",
            "fecha_inicio": "2026-09-01",
            "fecha_fin": "2027-02-28",
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:periodo_list") in response.url
        assert Periodo.objects.filter(nombre="2026-B").exists()

    # --- Update ---

    def test_update_periodo_get(self):
        """GET /academico/periodos/<pk>/editar/ → 200, form populated, editing=True."""
        periodo = _create_periodo(creado_por=self.inspector)

        url = reverse("academico:periodo_update", args=[periodo.pk])
        response = self.client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["editing"] is True

    def test_update_periodo_post_exitoso(self):
        """POST updated data → redirects to periodo_list, DB updated."""
        periodo = _create_periodo(creado_por=self.inspector)

        url = reverse("academico:periodo_update", args=[periodo.pk])
        data = {
            "nombre": "2026-A-Modificado",
            "fecha_inicio": "2026-03-01",
            "fecha_fin": "2026-08-31",
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:periodo_list") in response.url

        periodo.refresh_from_db()
        assert periodo.nombre == "2026-A-Modificado"
        assert periodo.fecha_fin == datetime.date(2026, 8, 31)


# =============================================================================
# TestAsignaturaViews — 4 tests
# =============================================================================


@pytest.mark.django_db
class TestAsignaturaViews:
    """View tests for subject CRUD (HU06)."""

    def setup_method(self):
        self.client = Client()
        self.inspector = _create_inspector()
        self.client.force_login(self.inspector)
        self.tipo_licencia = _create_tipo_licencia()

    # --- List ---

    def test_list_asignaturas_inspector(self):
        """GET /academico/asignaturas/ as inspector → 200."""
        _create_asignatura()

        url = reverse("academico:asignatura_list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "academico/asignatura_list.html" in [t.name for t in response.templates]
        assert "asignaturas" in response.context

    def test_list_asignaturas_estudiante_forbidden(self):
        """GET /academico/asignaturas/ as estudiante → 403."""
        estudiante_client = Client()
        estudiante = _create_estudiante()
        estudiante_client.force_login(estudiante)

        url = reverse("academico:asignatura_list")
        response = estudiante_client.get(url)

        assert response.status_code == 403

    # --- Create ---

    def test_create_asignatura_post_exitoso(self):
        """POST with valid data → redirect to asignatura_list, created in DB."""
        url = reverse("academico:asignatura_create")
        data = {
            "nombre": "Mecánica Automotriz",
            "codigo": "MEC-001",
            "descripcion": "Curso de mecánica",
            "horas_lectivas": 60,
            "tipos_licencia": [self.tipo_licencia.pk],
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:asignatura_list") in response.url
        assert Asignatura.objects.filter(codigo="MEC-001").exists()
        asig = Asignatura.objects.get(codigo="MEC-001")
        assert asig.tipos_licencia.count() == 1
        assert asig.horas_lectivas == 60

    # --- Update ---

    def test_update_asignatura_post_exitoso(self):
        """POST updated data → redirect to asignatura_list, DB updated."""
        asig = _create_asignatura()
        asig.tipos_licencia.add(self.tipo_licencia)

        url = reverse("academico:asignatura_update", args=[asig.pk])
        data = {
            "nombre": "Legislación Actualizada",
            "codigo": "LEG-001",
            "descripcion": "Descripción actualizada",
            "horas_lectivas": 50,
            "tipos_licencia": [self.tipo_licencia.pk],
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:asignatura_list") in response.url

        asig.refresh_from_db()
        assert asig.nombre == "Legislación Actualizada"
        assert asig.horas_lectivas == 50


# =============================================================================
# TestParaleloViews — 4 tests
# =============================================================================


@pytest.mark.django_db
class TestParaleloViews:
    """View tests for parallel CRUD (HU06)."""

    def setup_method(self):
        self.client = Client()
        self.inspector = _create_inspector()
        self.client.force_login(self.inspector)

        self.docente = _create_docente()
        self.tipo_licencia = _create_tipo_licencia()
        self.periodo = _create_periodo(creado_por=self.inspector, activo=True)
        self.asignatura = _create_asignatura()
        self.asignatura.tipos_licencia.add(self.tipo_licencia)

    # --- List ---

    def test_list_paralelos_inspector(self):
        """GET /academico/paralelos/ as inspector → 200."""
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            horario="Lun-Mie 08:00-10:00",
            capacidad_maxima=30,
        )

        url = reverse("academico:paralelo_list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "academico/paralelo_list.html" in [t.name for t in response.templates]
        assert "paralelos" in response.context

    def test_list_paralelos_docente_forbidden(self):
        """GET /academico/paralelos/ as docente → 403."""
        docente_client = Client()
        docente_client.force_login(self.docente)

        url = reverse("academico:paralelo_list")
        response = docente_client.get(url)

        assert response.status_code == 403

    # --- Create ---

    def test_create_paralelo_post_exitoso(self):
        """POST with all required fields → redirect to paralelo_list, created in DB."""
        url = reverse("academico:paralelo_create")
        data = {
            "asignatura": self.asignatura.pk,
            "periodo": self.periodo.pk,
            "tipo_licencia": self.tipo_licencia.pk,
            "docente": self.docente.pk,
            "nombre": "B",
            "horario": "Mar-Jue 10:00-12:00",
            "capacidad_maxima": 25,
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:paralelo_list") in response.url
        assert Paralelo.objects.filter(nombre="B").exists()
        paralelo = Paralelo.objects.get(nombre="B")
        assert paralelo.capacidad_maxima == 25
        assert paralelo.docente == self.docente

    # --- Update ---

    def test_update_paralelo_post_exitoso(self):
        """POST updated data → redirect to paralelo_list, DB updated."""
        paralelo = Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            horario="Lun-Mie 08:00-10:00",
            capacidad_maxima=30,
        )

        url = reverse("academico:paralelo_update", args=[paralelo.pk])
        data = {
            "asignatura": self.asignatura.pk,
            "periodo": self.periodo.pk,
            "tipo_licencia": self.tipo_licencia.pk,
            "docente": self.docente.pk,
            "nombre": "A",
            "horario": "Lun-Vie 14:00-16:00",
            "capacidad_maxima": 35,
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:paralelo_list") in response.url

        paralelo.refresh_from_db()
        assert paralelo.capacidad_maxima == 35
        assert paralelo.horario == "Lun-Vie 14:00-16:00"


# =============================================================================
# TestTipoLicenciaViews — 2 tests
# =============================================================================


@pytest.mark.django_db
class TestTipoLicenciaViews:
    """View tests for license type listing (read-only)."""

    def setup_method(self):
        self.client = Client()
        self.inspector = _create_inspector()
        self.client.force_login(self.inspector)

    def test_list_tipos_licencia_inspector(self):
        """GET /academico/tipos-licencia/ as inspector → 200, correct template and context."""
        _create_tipo_licencia()

        url = reverse("academico:tipo_licencia_list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert "academico/tipo_licencia_list.html" in [
            t.name for t in response.templates
        ]
        assert "tipos_licencia" in response.context

    def test_list_tipos_licencia_docente_forbidden(self):
        """GET /academico/tipos-licencia/ as docente → 403."""
        docente_client = Client()
        docente = _create_docente()
        docente_client.force_login(docente)

        url = reverse("academico:tipo_licencia_list")
        response = docente_client.get(url)

        assert response.status_code == 403
