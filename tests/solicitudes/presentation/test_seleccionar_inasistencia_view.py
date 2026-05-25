"""Tests for SeleccionarInasistenciaView (HU20 — UI integration).

This view is the intermediate landing page between the dashboard/sidebar
"Justificación" entry points and the certificate form. It lists the
authenticated estudiante's justifiable absences (AUSENTE attendance rows
in active periods with active enrollment) and links each one to the HU20
certificate form.

Reuses `SolicitudAppService.obtener_inasistencias_justificables` which is
already covered by HU18 tests, so we focus on view-level concerns:
access control, rendering, and the link to the HU20 form.
"""

import datetime

import pytest
from django.urls import reverse

from apps.asistencia.infrastructure.models import Asistencia
from apps.usuarios.infrastructure.models import Usuario
from tests.factories import (
    AsistenciaFactory,
    DocenteFactory,
    EstudianteFactory,
    InspectorFactory,
    MatriculaFactory,
    ParaleloFactory,
    PeriodoFactory,
    UsuarioFactory,
)


# -------------------------------------------------------------------- #
# Helpers
# -------------------------------------------------------------------- #


URL = reverse("solicitudes:seleccionar_inasistencia")


@pytest.fixture
def estudiante_con_inasistencias(db):
    """Estudiante matriculado en período activo con 2 inasistencias AUSENTE."""
    actor = DocenteFactory()
    actor.save()
    periodo = PeriodoFactory(activo=True)
    paralelo = ParaleloFactory(periodo=periodo)
    estudiante = EstudianteFactory()
    estudiante.save()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo, matriculado_por=actor)
    asistencia1 = AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        estado=Asistencia.Estado.AUSENTE,
        fecha=datetime.date(2026, 4, 1),
    )
    asistencia2 = AsistenciaFactory(
        estudiante=estudiante,
        paralelo=paralelo,
        estado=Asistencia.Estado.AUSENTE,
        fecha=datetime.date(2026, 4, 8),
    )
    return estudiante, [asistencia1, asistencia2]


@pytest.fixture
def estudiante_sin_inasistencias(db):
    """Estudiante matriculado en período activo pero sin inasistencias AUSENTE."""
    actor = DocenteFactory()
    actor.save()
    periodo = PeriodoFactory(activo=True)
    paralelo = ParaleloFactory(periodo=periodo)
    estudiante = EstudianteFactory()
    estudiante.save()
    MatriculaFactory(estudiante=estudiante, paralelo=paralelo, matriculado_por=actor)
    return estudiante


# -------------------------------------------------------------------- #
# Access control
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestAccesoControl:
    def test_anonymous_redirects_to_login(self, client):
        resp = client.get(URL)
        assert resp.status_code == 302
        assert "/usuarios/login/" in resp.url

    @pytest.mark.parametrize(
        "factory_callable",
        [
            lambda: DocenteFactory(),
            lambda: InspectorFactory(),
            lambda: UsuarioFactory(rol=Usuario.Rol.SECRETARIA),
        ],
        ids=["docente", "inspector", "secretaria"],
    )
    def test_no_estudiante_forbidden(self, client, factory_callable):
        user = factory_callable()
        user.save()
        client.force_login(user)
        resp = client.get(URL)
        assert resp.status_code == 403


# -------------------------------------------------------------------- #
# Render: empty state
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestEstadoVacio:
    def test_estudiante_sin_inasistencias_ve_estado_vacio(
        self, client, estudiante_sin_inasistencias
    ):
        client.force_login(estudiante_sin_inasistencias)
        resp = client.get(URL)
        assert resp.status_code == 200
        # Empty-state copy borrowed from the legacy template.
        assert b"No tiene inasistencias por justificar" in resp.content


# -------------------------------------------------------------------- #
# Render: list
# -------------------------------------------------------------------- #


@pytest.mark.django_db
class TestListaInasistencias:
    def test_estudiante_con_inasistencias_ve_lista(self, client, estudiante_con_inasistencias):
        estudiante, asistencias = estudiante_con_inasistencias
        client.force_login(estudiante)
        resp = client.get(URL)
        assert resp.status_code == 200
        # Each absence should be rendered with its asignatura code.
        for asis in asistencias:
            codigo = asis.paralelo.asignatura.codigo.encode()
            assert codigo in resp.content

    def test_cada_inasistencia_linkea_a_form_certificado(
        self, client, estudiante_con_inasistencias
    ):
        estudiante, asistencias = estudiante_con_inasistencias
        client.force_login(estudiante)
        resp = client.get(URL)
        assert resp.status_code == 200
        for asis in asistencias:
            expected_url = reverse(
                "solicitudes:crear_justificacion_certificado",
                args=[asis.id],
            )
            assert expected_url.encode() in resp.content

    def test_solo_muestra_inasistencias_propias(self, client, estudiante_con_inasistencias):
        estudiante, asistencias_propias = estudiante_con_inasistencias
        # Create another estudiante in the same paralelo with their own absence.
        otro = EstudianteFactory()
        otro.save()
        paralelo = asistencias_propias[0].paralelo
        actor = DocenteFactory()
        actor.save()
        MatriculaFactory(estudiante=otro, paralelo=paralelo, matriculado_por=actor)
        asistencia_ajena = AsistenciaFactory(
            estudiante=otro,
            paralelo=paralelo,
            estado=Asistencia.Estado.AUSENTE,
            fecha=datetime.date(2026, 4, 15),
        )

        client.force_login(estudiante)
        resp = client.get(URL)
        assert resp.status_code == 200
        # Link to other student's absence must NOT appear.
        ajena_url = reverse(
            "solicitudes:crear_justificacion_certificado",
            args=[asistencia_ajena.id],
        )
        assert ajena_url.encode() not in resp.content
