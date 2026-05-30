"""
View tests for the Academico bounded context using Django test Client.

Tests: PeriodoListView, PeriodoCreateView, PeriodoUpdateView,
       AsignaturaListView, AsignaturaCreateView, AsignaturaUpdateView,
       ParaleloListView, ParaleloCreateView, ParaleloUpdateView,
       TipoLicenciaListView.
Role enforcement: all views require Inspector or Secretaria — other roles get 403.
Refs: HU05, HU06, SCN-PER-01→04, SCN-CAT-01→10
"""

import datetime

import pytest
from django.test import Client
from django.urls import reverse

from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    BloqueHorario,
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
        cedula="1701000001",
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
        cedula="1701000002",
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
        cedula="1701000003",
    )


def _create_secretaria() -> Usuario:
    return Usuario.objects.create_user(
        username="secretaria_v",
        email="secretaria@v.com",
        password=PASSWORD,
        first_name="Ana",
        last_name="Martinez",
        rol="secretaria",
        is_active=True,
        cedula="1701000004",
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
        codigo=codigo,
        defaults=defaults,
    )
    for key, val in defaults.items():
        setattr(obj, key, val)
    obj.save()
    return obj


def _create_periodo(creado_por=None, tipo_licencia=None, **kwargs) -> Periodo:
    defaults = {
        "nombre": "2026-A",
        "fecha_inicio": datetime.date(2026, 3, 1),
        "fecha_fin": datetime.date(2026, 7, 31),
        "activo": True,
    }
    defaults.update(kwargs)
    if creado_por:
        defaults["creado_por"] = creado_por
    if tipo_licencia is None:
        tipo_licencia = _create_tipo_licencia()
    defaults["tipo_licencia"] = tipo_licencia
    return Periodo.objects.create(**defaults)


def _create_asignatura(**kwargs) -> Asignatura:
    defaults = {
        "nombre": "Legislación de Tránsito",
        "codigo": "LEG-001",
        "descripcion": "Descripción de prueba",
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
        tipo_licencia = _create_tipo_licencia()
        url = reverse("academico:periodo_create")
        data = {
            "nombre": "2026-B",
            "tipo_licencia": tipo_licencia.pk,
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
            "tipo_licencia": periodo.tipo_licencia.pk,
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
            f"tipo_licencia_{self.tipo_licencia.pk}": "on",
            f"horas_{self.tipo_licencia.pk}": 60,
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:asignatura_list") in response.url
        assert Asignatura.objects.filter(codigo="MEC-001").exists()
        asig = Asignatura.objects.get(codigo="MEC-001")
        assert asig.asignatura_licencias.count() == 1
        assert asig.asignatura_licencias.first().horas_lectivas == 60

    # --- Update ---

    def test_update_asignatura_post_exitoso(self):
        """POST updated data → redirect to asignatura_list, DB updated."""
        asig = _create_asignatura()
        AsignaturaLicencia.objects.create(
            asignatura=asig, tipo_licencia=self.tipo_licencia, horas_lectivas=40
        )

        url = reverse("academico:asignatura_update", args=[asig.pk])
        data = {
            "nombre": "Legislación Actualizada",
            "codigo": "LEG-001",
            "descripcion": "Descripción actualizada",
            f"tipo_licencia_{self.tipo_licencia.pk}": "on",
            f"horas_{self.tipo_licencia.pk}": 50,
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:asignatura_list") in response.url

        asig.refresh_from_db()
        assert asig.nombre == "Legislación Actualizada"
        al = asig.asignatura_licencias.first()
        assert al.horas_lectivas == 50


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
        AsignaturaLicencia.objects.create(
            asignatura=self.asignatura,
            tipo_licencia=self.tipo_licencia,
            horas_lectivas=40,
        )

    # --- List ---

    def test_list_paralelos_inspector(self):
        """GET /academico/paralelos/ as inspector → 200."""
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
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
        """POST updated docente → redirect to paralelo_list, DB updated."""
        paralelo = Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )

        url = reverse("academico:paralelo_update", args=[paralelo.pk])
        data = {
            "docente": self.docente.pk,
        }

        response = self.client.post(url, data)

        assert response.status_code == 302
        assert reverse("academico:paralelo_list") in response.url

        paralelo.refresh_from_db()
        assert paralelo.docente == self.docente


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
        assert "academico/tipo_licencia_list.html" in [t.name for t in response.templates]
        assert "tipos_licencia" in response.context

    def test_list_tipos_licencia_docente_forbidden(self):
        """GET /academico/tipos-licencia/ as docente → 403."""
        docente_client = Client()
        docente = _create_docente()
        docente_client.force_login(docente)

        url = reverse("academico:tipo_licencia_list")
        response = docente_client.get(url)

        assert response.status_code == 403


# =============================================================================
# TestSecretariaAccess — 3 tests
# =============================================================================


@pytest.mark.django_db
class TestSecretariaAccess:
    """Verify secretaria role can access all academic views."""

    def setup_method(self):
        self.client = Client()
        self.secretaria = _create_secretaria()
        self.client.force_login(self.secretaria)

        self.inspector = _create_inspector()
        self.tipo_licencia = _create_tipo_licencia()
        self.periodo = _create_periodo(creado_por=self.inspector, activo=True)
        self.asignatura = _create_asignatura()
        AsignaturaLicencia.objects.create(
            asignatura=self.asignatura,
            tipo_licencia=self.tipo_licencia,
            horas_lectivas=40,
        )
        self.docente = _create_docente()

    def test_secretaria_can_list_periodos(self):
        """GET /academico/periodos/ as secretaria → 200."""
        url = reverse("academico:periodo_list")
        response = self.client.get(url)
        assert response.status_code == 200

    def test_secretaria_can_list_asignaturas(self):
        """GET /academico/asignaturas/ as secretaria → 200."""
        url = reverse("academico:asignatura_list")
        response = self.client.get(url)
        assert response.status_code == 200

    def test_secretaria_can_list_paralelos(self):
        """GET /academico/paralelos/ as secretaria → 200."""
        Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )
        url = reverse("academico:paralelo_list")
        response = self.client.get(url)
        assert response.status_code == 200


# =============================================================================
# TestParaleloLoteViews — 7 tests
# =============================================================================


@pytest.mark.django_db
class TestParaleloLoteViews:
    """View tests for batch paralelo creation."""

    def setup_method(self):
        self.client = Client()
        self.inspector = _create_inspector()
        self.client.force_login(self.inspector)

        self.docente = _create_docente()
        self.tipo_licencia = _create_tipo_licencia(num_asignaturas=5)
        self.periodo = _create_periodo(creado_por=self.inspector, activo=True)

        self.asig1 = _create_asignatura(nombre="Legislación", codigo="LEG-001")
        self.asig2 = _create_asignatura(nombre="Mecánica", codigo="MEC-001")
        self.asig3 = _create_asignatura(nombre="Primeros Auxilios", codigo="PAU-001")
        AsignaturaLicencia.objects.create(
            asignatura=self.asig1, tipo_licencia=self.tipo_licencia, horas_lectivas=40
        )
        AsignaturaLicencia.objects.create(
            asignatura=self.asig2, tipo_licencia=self.tipo_licencia, horas_lectivas=40
        )
        AsignaturaLicencia.objects.create(
            asignatura=self.asig3, tipo_licencia=self.tipo_licencia, horas_lectivas=40
        )

    def _lote_url(self):
        return reverse("academico:paralelo_create_lote")

    def _post_data(self, asignatura_ids):
        return {
            "periodo": self.periodo.pk,
            "tipo_licencia": self.tipo_licencia.pk,
            "asignaturas": asignatura_ids,
            "nombre": "A",
            "docente": self.docente.pk,
            "capacidad_maxima": 30,
        }

    def test_get_form_lote(self):
        """GET /academico/paralelos/crear-lote/ as inspector → 200."""
        response = self.client.get(self._lote_url())
        assert response.status_code == 200
        assert "academico/paralelo_form_lote.html" in [t.name for t in response.templates]

    def test_create_lote_exitoso(self):
        """POST with 3 asignaturas → creates 3 paralelos, redirect."""
        data = self._post_data([self.asig1.pk, self.asig2.pk, self.asig3.pk])
        response = self.client.post(self._lote_url(), data)

        assert response.status_code == 302
        assert reverse("academico:paralelo_list") in response.url
        assert Paralelo.objects.count() == 3
        assert Paralelo.objects.filter(nombre="A", tipo_licencia=self.tipo_licencia).count() == 3

    def test_create_lote_skips_duplicates(self):
        """POST with existing paralelo → skips duplicate, creates the rest."""
        Paralelo.objects.create(
            asignatura=self.asig1,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )

        data = self._post_data([self.asig1.pk, self.asig2.pk])
        response = self.client.post(self._lote_url(), data)

        assert response.status_code == 302
        assert Paralelo.objects.count() == 2  # 1 existing + 1 new

    def test_create_lote_no_asignaturas_selected(self):
        """POST without asignaturas → form error, no paralelos created."""
        data = self._post_data([])
        response = self.client.post(self._lote_url(), data)

        assert response.status_code == 200  # re-render form
        assert Paralelo.objects.count() == 0

    def test_create_lote_exceeds_max_asignaturas(self):
        """POST with more asignaturas than tipo_licencia.num_asignaturas → form error."""
        # tipo_licencia has num_asignaturas=5, create 6 asignaturas
        extra_asigs = []
        for i in range(4, 7):
            asig = _create_asignatura(nombre=f"Extra {i}", codigo=f"EXT-{i:03d}")
            AsignaturaLicencia.objects.create(
                asignatura=asig, tipo_licencia=self.tipo_licencia, horas_lectivas=40
            )
            extra_asigs.append(asig)

        all_ids = [self.asig1.pk, self.asig2.pk, self.asig3.pk] + [a.pk for a in extra_asigs]
        assert len(all_ids) == 6  # exceeds 5

        data = self._post_data(all_ids)
        response = self.client.post(self._lote_url(), data)

        assert response.status_code == 200  # re-render form with error
        assert Paralelo.objects.count() == 0

    def test_create_lote_docente_forbidden(self):
        """POST as docente → 403."""
        docente_client = Client()
        docente_client.force_login(self.docente)

        data = self._post_data([self.asig1.pk])
        response = docente_client.post(self._lote_url(), data)

        assert response.status_code == 403

    def test_asignaturas_por_tipo_json(self):
        """GET /academico/asignaturas-por-tipo/?tipo_licencia=X
        → JSON with filtered asignaturas."""
        url = reverse("academico:asignaturas_por_tipo")
        response = self.client.get(url, {"tipo_licencia": self.tipo_licencia.pk})

        assert response.status_code == 200
        data = response.json()
        assert len(data["asignaturas"]) == 3
        codigos = {a["codigo"] for a in data["asignaturas"]}
        assert codigos == {"LEG-001", "MEC-001", "PAU-001"}


# =============================================================================
# TestParaleloBloqueHorarioViews — 5 tests
# =============================================================================


@pytest.mark.django_db
class TestParaleloBloqueHorarioViews:
    """View tests for BloqueHorario management in ParaleloUpdateView."""

    def setup_method(self):
        self.client = Client()
        self.inspector = _create_inspector()
        self.client.force_login(self.inspector)

        self.docente = _create_docente()
        self.tipo_licencia = _create_tipo_licencia()
        self.periodo = _create_periodo(creado_por=self.inspector, activo=True)
        self.asignatura = _create_asignatura(nombre="Legislación", codigo="LEG-001")
        AsignaturaLicencia.objects.create(
            asignatura=self.asignatura,
            tipo_licencia=self.tipo_licencia,
            horas_lectivas=40,
        )

        self.paralelo = Paralelo.objects.create(
            asignatura=self.asignatura,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )

    def _update_url(self):
        return reverse("academico:paralelo_update", args=[self.paralelo.pk])

    def _post_with_bloques(self, bloques):
        """Helper: POST docente + schedule blocks."""
        data = {"docente": self.docente.pk}
        for i, b in enumerate(bloques):
            data[f"bloque_dia_{i}"] = b["dia"]
            data[f"bloque_inicio_{i}"] = b["inicio"]
            data[f"bloque_fin_{i}"] = b["fin"]
        data["bloques_count"] = len(bloques)
        return self.client.post(self._update_url(), data)

    def test_update_paralelo_adds_bloques(self):
        """POST with docente + 2 schedule blocks → blocks created in DB."""
        bloques = [
            {"dia": "lunes", "inicio": "08:00", "fin": "10:00"},
            {"dia": "miercoles", "inicio": "08:00", "fin": "10:00"},
        ]
        response = self._post_with_bloques(bloques)

        assert response.status_code == 302
        assert BloqueHorario.objects.filter(paralelo=self.paralelo).count() == 2

    def test_update_paralelo_replaces_bloques(self):
        """Create existing blocks, POST new ones → old deleted, new created."""
        BloqueHorario.objects.create(
            paralelo=self.paralelo,
            dia_semana="lunes",
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(10, 0),
        )
        assert BloqueHorario.objects.filter(paralelo=self.paralelo).count() == 1

        bloques = [
            {"dia": "martes", "inicio": "14:00", "fin": "16:00"},
            {"dia": "jueves", "inicio": "14:00", "fin": "16:00"},
        ]
        response = self._post_with_bloques(bloques)

        assert response.status_code == 302
        db_bloques = BloqueHorario.objects.filter(paralelo=self.paralelo)
        assert db_bloques.count() == 2
        assert not db_bloques.filter(dia_semana="lunes").exists()

    def test_update_paralelo_conflict_detected(self):
        """Block on another paralelo in same group with
        overlapping time → error, blocks NOT saved."""
        # Create another asignatura in same group
        asig2 = _create_asignatura(nombre="Mecánica", codigo="MEC-001")
        AsignaturaLicencia.objects.create(
            asignatura=asig2, tipo_licencia=self.tipo_licencia, horas_lectivas=40
        )
        paralelo2 = Paralelo.objects.create(
            asignatura=asig2,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )
        BloqueHorario.objects.create(
            paralelo=paralelo2,
            dia_semana="lunes",
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(10, 0),
        )

        # Try to add overlapping block
        bloques = [{"dia": "lunes", "inicio": "09:00", "fin": "11:00"}]
        response = self._post_with_bloques(bloques)

        assert response.status_code == 200  # re-rendered form
        assert BloqueHorario.objects.filter(paralelo=self.paralelo).count() == 0
        assert "Conflicto de horario" in response.content.decode()

    def test_update_paralelo_no_conflict_different_day(self):
        """Same group but different day → no conflict, saves OK."""
        asig2 = _create_asignatura(nombre="Mecánica", codigo="MEC-002")
        AsignaturaLicencia.objects.create(
            asignatura=asig2, tipo_licencia=self.tipo_licencia, horas_lectivas=40
        )
        paralelo2 = Paralelo.objects.create(
            asignatura=asig2,
            periodo=self.periodo,
            tipo_licencia=self.tipo_licencia,
            docente=self.docente,
            nombre="A",
            capacidad_maxima=30,
        )
        BloqueHorario.objects.create(
            paralelo=paralelo2,
            dia_semana="lunes",
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(10, 0),
        )

        # Different day → no conflict
        bloques = [{"dia": "martes", "inicio": "08:00", "fin": "10:00"}]
        response = self._post_with_bloques(bloques)

        assert response.status_code == 302
        assert BloqueHorario.objects.filter(paralelo=self.paralelo).count() == 1

    def test_update_paralelo_invalid_times(self):
        """hora_inicio >= hora_fin → error shown, blocks NOT saved."""
        bloques = [{"dia": "lunes", "inicio": "10:00", "fin": "08:00"}]
        response = self._post_with_bloques(bloques)

        assert response.status_code == 200  # re-rendered form
        assert BloqueHorario.objects.filter(paralelo=self.paralelo).count() == 0
        assert "Horario inválido" in response.content.decode()
